from __future__ import annotations
import base64, hashlib, hmac, json, time, uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional
import httpx, jwt
from cryptography.hazmat.primitives import serialization
from app.config import settings

class PlatformProviderError(Exception): pass

def _client():
    from .main import _pinned_public_http_client
    return _pinned_public_http_client(20)

def _money(v): return f"{Decimal(str(v)).quantize(Decimal('0.01')):.2f}"

class StripePlatform:
    name='stripe'
    async def create(self, amount, currency, description, metadata):
        if not settings.stripe_secret_key: raise PlatformProviderError('Stripe is not configured')
        async with _client() as c:
            data={'mode':'payment','success_url':metadata.get('return_url',settings.public_base_url),'cancel_url':metadata.get('cancel_url',settings.public_base_url),'line_items[0][price_data][currency]':currency.lower(),'line_items[0][price_data][product_data][name]':description,'line_items[0][price_data][unit_amount]':int(Decimal(str(amount))*100),'line_items[0][quantity]':1,'metadata[order_id]':metadata.get('order_id',''),'metadata[user_id]':str(metadata.get('user_id',''))}
            r=await c.post(f'{settings.stripe_api_url}/v1/checkout/sessions',data=data,headers={'Authorization':f'Bearer {settings.stripe_secret_key}'})
            r.raise_for_status(); x=r.json()
            return {'id':x['id'],'url':x.get('url'),'status':x.get('status')}
    async def create_recurring(self, amount, order_id, description, token):
        raise PlatformProviderError('Stripe recurring token requires a Stripe PaymentMethod/customer mapping; use SetupIntent/Customer flow')
    async def status(self,payment_id):
        async with _client() as c:
            r=await c.get(f'{settings.stripe_api_url}/v1/payment_intents/{payment_id}',headers={'Authorization':f'Bearer {settings.stripe_secret_key}'})
            r.raise_for_status(); return r.json()
    async def refund(self,payment_id,amount,currency,order_id=None):
        async with _client() as c:
            data={'payment_intent':payment_id,'amount':int(Decimal(str(amount))*100)}
            r=await c.post(f'{settings.stripe_api_url}/v1/refunds',data=data,headers={'Authorization':f'Bearer {settings.stripe_secret_key}'})
            r.raise_for_status(); return r.json()
    def verify_webhook(self, body:bytes, signature:str):
        if not settings.stripe_webhook_secret: raise PlatformProviderError('Stripe webhook secret is not configured')
        parts=dict(x.split('=',1) for x in signature.split(',') if '=' in x); ts=parts.get('t'); sig=parts.get('v1')
        if not ts or not sig or abs(time.time()-int(ts))>300: raise PlatformProviderError('Invalid Stripe webhook timestamp')
        expected=hmac.new(settings.stripe_webhook_secret.encode(),ts.encode()+b'.'+body,hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected,sig): raise PlatformProviderError('Invalid Stripe webhook signature')
        return json.loads(body)

class PayPalPlatform:
    name='paypal'
    async def _token(self):
        if not settings.paypal_client_id or not settings.paypal_client_secret: raise PlatformProviderError('PayPal is not configured')
        async with _client() as c:
            r=await c.post(f'{settings.paypal_api_url}/v1/oauth2/token',data={'grant_type':'client_credentials'},auth=(settings.paypal_client_id,settings.paypal_client_secret),headers={'Accept':'application/json'})
            r.raise_for_status(); return r.json()['access_token']
    async def create(self,amount,currency,description,metadata):
        token=await self._token()
        async with _client() as c:
            payload={'intent':'CAPTURE','purchase_units':[{'reference_id':metadata.get('order_id'),'description':description,'amount':{'currency_code':currency,'value':_money(amount)}}],'application_context':{'return_url':metadata.get('return_url',settings.public_base_url),'cancel_url':metadata.get('cancel_url',settings.public_base_url)}}
            r=await c.post(f'{settings.paypal_api_url}/v2/checkout/orders',json=payload,headers={'Authorization':f'Bearer {token}','Content-Type':'application/json','PayPal-Request-Id':metadata.get('order_id',str(uuid.uuid4()))}); r.raise_for_status(); x=r.json()
            url=next((l['href'] for l in x.get('links',[]) if l.get('rel')=='approve'),None)
            return {'id':x['id'],'url':url,'status':x.get('status')}
    async def capture(self,order_id):
        token=await self._token()
        async with _client() as c:
            r=await c.post(f'{settings.paypal_api_url}/v2/checkout/orders/{order_id}/capture',headers={'Authorization':f'Bearer {token}','Content-Type':'application/json'}); r.raise_for_status(); return r.json()
    async def refund(self,order_id,amount,currency,order_ref=None):
        token=await self._token()
        async with _client() as c:
            r=await c.get(f'{settings.paypal_api_url}/v2/checkout/orders/{order_id}',headers={'Authorization':f'Bearer {token}'})
            r.raise_for_status(); order=r.json()
            capture=((order.get('purchase_units') or [{}])[0].get('payments') or {}).get('captures') or []
            if not capture: raise PlatformProviderError('PayPal capture is not available for refund')
            capture_id=capture[0].get('id')
            r=await c.post(f'{settings.paypal_api_url}/v2/payments/captures/{capture_id}/refund',json={'amount':{'value':_money(amount),'currency_code':currency}},headers={'Authorization':f'Bearer {token}'})
            r.raise_for_status(); return r.json()
    async def verify_webhook(self,headers,body):
        # PayPal's verification endpoint is used rather than trusting a header locally.
        token=await self._token()
        async with _client() as c:
            payload={'auth_algo':headers.get('paypal-auth-algo'),'cert_url':headers.get('paypal-cert-url'),'transmission_id':headers.get('paypal-transmission-id'),'transmission_sig':headers.get('paypal-transmission-sig'),'transmission_time':headers.get('paypal-transmission-time'),'webhook_id':settings.paypal_webhook_id,'webhook_event':json.loads(body)}
            r=await c.post(f'{settings.paypal_api_url}/v1/notifications/verify-webhook-signature',json=payload,headers={'Authorization':f'Bearer {token}'})
            r.raise_for_status(); x=r.json()
            if x.get('verification_status')!='SUCCESS': raise PlatformProviderError('Invalid PayPal webhook signature')
            return payload['webhook_event']

class CryptoGatewayPlatform:
    name='crypto'
    async def create(self,amount,currency,description,metadata):
        if not settings.crypto_gateway_url or not settings.crypto_gateway_key: raise PlatformProviderError('Crypto gateway is not configured')
        async with _client() as c:
            r=await c.post(settings.crypto_gateway_url.rstrip('/')+'/payments',json={'amount':_money(amount),'currency':currency,'description':description,'order_id':metadata.get('order_id'),'return_url':metadata.get('return_url')},headers={'Authorization':f'Bearer {settings.crypto_gateway_key}'})
            r.raise_for_status(); return r.json()

class AppleStorePlatform:
    name='apple_iap'
    async def verify_transaction(self,signed_transaction:str):
        if not settings.apple_bundle_id: raise PlatformProviderError('Apple bundle id is not configured')
        # StoreKit 2 supplies JWS transactions. Decode for routing, then optionally
        # query App Store Server API when a signed transaction id is present.
        try:
            payload=jwt.decode(signed_transaction,options={'verify_signature':False,'verify_exp':False},algorithms=['ES256','RS256'])
        except Exception as e: raise PlatformProviderError(f'Invalid Apple transaction JWS: {e}')
        if payload.get('bundleId') and payload.get('bundleId')!=settings.apple_bundle_id: raise PlatformProviderError('Apple bundle id mismatch')
        if payload.get('transactionId'):
            data=await self.get_transaction(payload['transactionId'])
            signed=(data.get('signedTransactions') or [None])[0] if isinstance(data,dict) else None
            if signed:
                verified_payload=jwt.decode(signed,options={'verify_signature':False,'verify_exp':False},algorithms=['ES256','RS256'])
                if verified_payload.get('bundleId') != settings.apple_bundle_id: raise PlatformProviderError('Apple bundle id mismatch')
                if str(verified_payload.get('transactionId')) != str(payload.get('transactionId')): raise PlatformProviderError('Apple transaction id mismatch')
                return verified_payload
            return data
        return payload
    async def get_transaction(self,transaction_id):
        # Signed API token is generated only when App Store API credentials exist.
        if not (settings.apple_issuer_id and settings.apple_key_id and settings.apple_private_key): raise PlatformProviderError('Apple App Store Server API credentials are not configured')
        now=int(time.time()); key=settings.apple_private_key.replace('\\n','\n')
        token=jwt.encode({'iss':settings.apple_issuer_id,'iat':now,'exp':now+300,'aud':'appstoreconnect-v1'},key,algorithm='ES256',headers={'kid':settings.apple_key_id})
        async with _client() as c:
            r=await c.get(f'{settings.apple_appstore_api_url}/inApps/v1/transactions/{transaction_id}',headers={'Authorization':f'Bearer {token}'})
            r.raise_for_status(); return r.json()

class GooglePlayPlatform:
    name='google_play'
    async def _access_token(self):
        if not settings.google_service_account_json: raise PlatformProviderError('Google service account is not configured')
        info=json.loads(settings.google_service_account_json); now=int(time.time())
        key=info['private_key'].replace('\\n','\n'); assertion=jwt.encode({'iss':info['client_email'],'scope':'https://www.googleapis.com/auth/androidpublisher','aud':'https://oauth2.googleapis.com/token','iat':now,'exp':now+3600},key,algorithm='RS256')
        async with _client() as c:
            r=await c.post('https://oauth2.googleapis.com/token',data={'grant_type':'urn:ietf:params:oauth:grant-type:jwt-bearer','assertion':assertion}); r.raise_for_status(); return r.json()['access_token']
    async def verify_subscription(self,purchase_token):
        token=await self._access_token()
        async with _client() as c:
            r=await c.get(f'{settings.google_play_api_url}/androidpublisher/v3/applications/{settings.google_play_package}/purchases/subscriptionsv2/tokens/{purchase_token}',headers={'Authorization':f'Bearer {token}'}); r.raise_for_status(); return r.json()

PROVIDER_CAPABILITIES={
 'yookassa':{'cards':True,'recurring':True,'refunds':True,'currency':['RUB','EUR','USD']},
 'platega':{'cards':True,'recurring':False,'refunds':True,'currency':['RUB','EUR','USD']},
 'rollypay':{'cards':True,'recurring':False,'refunds':True,'currency':['RUB','EUR','USD']},
 'stripe':{'cards':True,'recurring':True,'refunds':True,'currency':['EUR','USD','GBP','RUB']},
 'paypal':{'cards':True,'paypal':True,'recurring':True,'refunds':True,'currency':['EUR','USD','GBP']},
 'crypto':{'crypto':True,'recurring':False,'refunds':False,'currency':['USD','EUR','USDT']},
 'apple_iap':{'app_store':True,'recurring':True},
 'google_play':{'play_store':True,'recurring':True},
 'sepa':{'bank_transfer':True,'recurring':True,'refunds':True,'currency':['EUR']},
 'sandbox':{'test':True},
}
