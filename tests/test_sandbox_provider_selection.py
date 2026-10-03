"""Settlement-only credentials must not disable a gateway-free test checkout."""
from types import SimpleNamespace
import pytest
from app import sandbox_mode


@pytest.mark.parametrize('agent', ['none','stripe','paypal','crypto','yookassa','rollypay','platega'])
def test_auto_selection_uses_only_supported_new_checkout_agents(monkeypatch,agent):
    config=SimpleNamespace(app_env='test',payments_sandbox=True,
        yookassa_shop_id='',yookassa_secret_key='',platega_merchant_id='',platega_secret='',
        rollypay_api_key='',stripe_secret_key='',paypal_client_id='',paypal_client_secret='',
        crypto_gateway_url='',crypto_gateway_key='')
    fields={'stripe':['stripe_secret_key'],'paypal':['paypal_client_id','paypal_client_secret'],
        'crypto':['crypto_gateway_url','crypto_gateway_key'],
        'yookassa':['yookassa_shop_id','yookassa_secret_key'],'rollypay':['rollypay_api_key'],
        'platega':['platega_merchant_id','platega_secret']}
    for field in fields.get(agent,[]):setattr(config,field,'configured')
    monkeypatch.setattr(sandbox_mode,'settings',config)
    supported=agent in {'yookassa','rollypay','platega'}
    assert sandbox_mode.live_checkout_configured() is supported
    assert sandbox_mode.sandbox_checkout_requested('auto') is (not supported)
    assert not sandbox_mode.sandbox_checkout_requested('yookassa')
    config.app_env='production'
    assert not sandbox_mode.sandbox_checkout_requested('sandbox')
