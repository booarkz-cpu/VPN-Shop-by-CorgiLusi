import {test,expect} from '@playwright/test';

test('browser registration, discoverable login, reload and credential deletion',async({page,context})=>{
  const client=await context.newCDPSession(page);
  await client.send('WebAuthn.enable');
  await client.send('WebAuthn.addVirtualAuthenticator',{options:{protocol:'ctap2',transport:'internal',
    hasResidentKey:true,hasUserVerification:true,isUserVerified:true,automaticPresenceSimulation:true}});
  await page.addInitScript(()=>localStorage.setItem('rw_lang','ru'));
  await page.goto('/');
  await page.getByLabel('Email',{exact:true}).fill('browser@example.test');
  await page.getByLabel('Пароль',{exact:true}).fill('browser-only-password');
  await page.getByRole('button',{name:'Войти',exact:true}).click();
  await page.getByRole('button',{name:/Ключи доступа/}).click();
  await expect(page.getByRole('heading',{name:'Ключи доступа / WebAuthn'})).toBeVisible();
  await page.getByLabel('Название',{exact:true}).fill('Browser authenticator');
  await page.getByLabel('Пароль',{exact:true}).fill('browser-only-password');
  await page.getByRole('button',{name:'Добавить ключ доступа'}).click();
  await expect(page.getByRole('cell',{name:'Browser authenticator'})).toBeVisible();
  await expect(page.getByLabel('Пароль',{exact:true})).toHaveValue('');
  await page.evaluate(async()=>{
    const csrf=decodeURIComponent(document.cookie.split('; ').find(x=>x.startsWith('rw_csrf='))?.split('=')[1]||'');
    const response=await fetch('/api/admin/auth/logout',{method:'POST',headers:{'X-CSRF-Token':csrf}});
    if (!response.ok) throw Error('Logout failed');
  });
  await page.reload();
  await page.getByRole('button',{name:'Войти с ключом доступа'}).click();
  await expect(page.getByRole('heading',{name:'Ключи доступа / WebAuthn'})).toBeVisible();
  await page.reload();
  await expect(page.getByRole('cell',{name:'Browser authenticator'})).toBeVisible();
  await page.getByRole('button',{name:'Удалить',exact:true}).click();
  await expect(page.getByText('Ключи ещё не добавлены.')).toBeVisible();
  await client.detach();
});
