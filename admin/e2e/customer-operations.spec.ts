import {test,expect} from '@playwright/test';
import {execFileSync} from 'node:child_process';

test('SQLite upload, mapping, confirmation, journal and bulk restriction',async({page})=>{
  const data=execFileSync(process.env.PASSKEY_TEST_PYTHON||'python',['-c',
    "import sqlite3,sys; c=sqlite3.connect(':memory:'); c.execute('create table legacy(tg integer,name text)'); c.execute(\"insert into legacy values(987654321, 'Import browser')\"); c.commit(); sys.stdout.buffer.write(c.serialize())"]);
  await page.addInitScript(()=>localStorage.setItem('rw_lang','ru'));
  await page.goto('/');
  await page.getByLabel('Email',{exact:true}).fill('browser@example.test');
  await page.getByLabel('Пароль',{exact:true}).fill('browser-only-password');
  await page.getByRole('button',{name:'Войти',exact:true}).click();
  await page.getByRole('button',{name:/Клиенты магазина/}).click();
  await page.getByText('Импорт пользователей и массовые операции',{exact:true}).click();
  await page.getByLabel('Автономный файл SQLite (до 8 МиБ)').setInputFiles({name:'users.db',mimeType:'application/octet-stream',buffer:data});
  await page.getByRole('button',{name:'Прочитать таблицы'}).click();
  await page.getByLabel('Название источника').fill('Browser migration');
  await page.getByLabel('Колонка Telegram ID').selectOption('tg');
  await page.getByLabel('Колонка имени').selectOption('name');
  await page.getByRole('button',{name:'Предпросмотр импорта'}).click();
  await expect(page.getByRole('heading',{name:'Предпросмотр: 1 записей'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Применить',exact:true})).toBeDisabled();
  await page.getByLabel('Проверил список и подтверждаю действие').check();
  const applied=page.waitForResponse(r=>r.url().endsWith('/apply'));
  await page.getByRole('button',{name:'Применить',exact:true}).click();
  const result=await (await applied).json();
  await expect(page.getByText('Операция завершена: 1 записей. Результат сохранён в журнале.')).toBeVisible();
  await page.getByLabel('ID клиентов магазина (до 500)').fill(String(result.rows[0].user_id));
  await page.getByLabel('Причина',{exact:true}).fill('Browser test restriction');
  await page.getByRole('button',{name:'Проверить выбранных клиентов'}).click();
  await page.getByLabel('Проверил список и подтверждаю действие').check();
  // Editing the intent invalidates confirmation and requires a fresh preview.
  await page.getByLabel('Причина',{exact:true}).fill('Reviewed browser restriction');
  await expect(page.getByRole('button',{name:'Применить',exact:true})).toHaveCount(0);
  await page.getByRole('button',{name:'Проверить выбранных клиентов'}).click();
  await page.getByLabel('Проверил список и подтверждаю действие').check();
  await page.getByRole('button',{name:'Применить',exact:true}).click();
  await expect(page.getByText('Операция завершена: 1 записей. Результат сохранён в журнале.')).toBeVisible();
  await expect(page.getByRole('cell',{name:'Reviewed browser restriction',exact:true})).toBeVisible();
});
