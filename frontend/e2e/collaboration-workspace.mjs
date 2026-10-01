// Use an isolated test database and fixture accounts, never company data.
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { readFile, mkdir } from 'node:fs/promises';
const sessions=JSON.parse(await readFile(process.env.WORKSPACE_SESSION_FILE,'utf8'));
const base=process.env.WORKSPACE_BASE_URL ?? 'http://127.0.0.1:4421';
const screenshots=process.env.WORKSPACE_SCREENSHOTS;
if(screenshots)await mkdir(screenshots,{recursive:true});
const browser=await chromium.launch({headless:true, channel:process.env.WORKSPACE_BROWSER_CHANNEL || undefined});
const context=await browser.newContext({viewport:{width:1440,height:960},reducedMotion:'reduce'});
const assignedName='Browser-created task '+Date.now();const messageName='Browser fixture: shared decision and notes. '+Date.now();
const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
async function signIn(role){await page.goto(base+'/login');await page.evaluate(tokens=>{localStorage.setItem('pl.access',tokens.access);localStorage.setItem('pl.refresh',tokens.refresh);},sessions[role]);}
async function noOverflow(label){assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,label+' horizontal overflow');}
async function snapshot(name){if(screenshots){await page.evaluate(()=>{window.scrollTo(0,0);return document.fonts.ready;});await page.screenshot({path:screenshots+'/'+name+'.png',fullPage:true});}}
async function engineering(){await page.getByRole('button',{name:'Engineering · browser fixture Department',exact:true}).click();}
try{
 await signIn('ceo');await page.goto(base+'/work');
 await page.getByRole('heading',{name:'Give every task a next step.'}).waitFor();
 await page.getByRole('button',{name:'Load more tasks',exact:true}).waitFor();await noOverflow('desktop board');
 assert.match(await page.locator('body').evaluate(e=>getComputedStyle(e).fontFamily),/Space Grotesk/);
 const initialCount=parseInt(await page.getByText(/tasks in your scope ·/).textContent(),10);
 await page.getByRole('button',{name:'Load more tasks',exact:true}).click();await page.waitForFunction(count=>document.querySelectorAll('.task-card').length===count,initialCount);
 const task=page.locator('.task-card').filter({has:page.getByRole('heading',{name:'Review workspace release',exact:true})});
 await task.locator('select').first().selectOption('in_progress');
 await page.waitForFunction(()=>[...document.querySelectorAll('.kanban-column')].some(c=>c.querySelector('h3')?.textContent.includes('In progress') && c.textContent.includes('Review workspace release')));
 await page.reload();await page.locator('.task-card').filter({hasText:'Review workspace release'}).waitFor();
 assert.equal(await page.locator('.task-card').filter({hasText:'Review workspace release'}).locator('select').first().inputValue(),'in_progress');
 await page.getByRole('button',{name:'List',exact:true}).click();await page.locator('.work-table').waitFor();await noOverflow('desktop list');
 await page.getByRole('button',{name:'Board',exact:true}).click();await page.locator('details.assignment-panel > summary').click();
 await page.locator('select[name=assignee]').selectOption({label:'Engineering reviewer · EN-P002'});
 await page.locator('select[name=project]').selectOption({label:'Workspace browser fixture'});
 await page.locator('textarea[name=text]').fill(assignedName);await page.locator('select[name=assignmentPriority]').selectOption('urgent');await page.locator('input[name=assignmentDeadline]').fill('2026-10-02');
 await page.getByRole('button',{name:'Assign work',exact:false}).click();await page.getByText('Work assigned.',{exact:true}).waitFor();
 await page.locator('.task-card').filter({hasText:assignedName}).waitFor();await snapshot('board-desktop');
 await page.goto(base+'/reports');await page.locator('textarea[name=completed]').waitFor();
 await page.locator('textarea[name=completed]').fill('Verified workspace end to end.');await page.locator('textarea[name=tomorrow]').fill('Review team feedback.');await page.locator('textarea[name=blockers]').fill('Waiting for deployment approval.');
 await page.getByRole('button',{name:/Submit daily report|Save changes/}).click();await page.getByText('Your daily report is saved.',{exact:true}).waitFor();await page.locator('.report-card').filter({hasText:'Verified workspace end to end.'}).waitFor();
 await page.reload();await page.waitForFunction(()=>document.querySelector('textarea[name=completed]')?.value==='Verified workspace end to end.');
 await page.locator('textarea[name=completed]').fill('Verified and updated workspace.');await page.getByRole('button',{name:'Save changes'}).click();await page.getByText('Your daily report is saved.',{exact:true}).waitFor();await page.locator('.report-card').filter({hasText:'Verified and updated workspace.'}).waitFor();assert.equal(await page.locator('.report-card').count(),1);await snapshot('reports-desktop');await noOverflow('desktop reports');
 await page.goto(base+'/chat');await engineering();await page.getByRole('button',{name:'Load older messages',exact:true}).waitFor();await page.getByRole('button',{name:'Load older messages',exact:true}).click();await page.waitForFunction(()=>document.querySelectorAll('.message').length===100);
 await page.locator('input[name=historySearch]').fill('Browser history 000');await page.getByRole('button',{name:'Search',exact:true}).click();await page.getByText('Browser history 000',{exact:true}).waitFor();assert.equal(await page.locator('.message').count(),1);
 if(await page.getByRole('button',{name:'Unpin message by Engineering reviewer',exact:true}).count()){await page.getByRole('button',{name:'Unpin message by Engineering reviewer',exact:true}).click();await page.getByRole('button',{name:'Pin message by Engineering reviewer',exact:true}).waitFor();}
 await page.getByRole('button',{name:'Pin message by Engineering reviewer',exact:true}).click();await page.getByText('Pinned decision',{exact:true}).waitFor();await page.getByRole('button',{name:'Pinned decisions',exact:true}).click();await page.getByText('Browser history 000',{exact:true}).waitFor();
 await page.locator('textarea[name=message]').fill(messageName);await page.locator('input[type=file]').setInputFiles({name:'review-notes.txt',mimeType:'text/plain',buffer:Buffer.from('Workspace browser fixture notes')});
 await page.getByRole('button',{name:'Send message',exact:false}).click();await page.getByText(messageName,{exact:true}).waitFor();
 const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'↓ review-notes.txt',exact:true}).last().click();const download=await downloadPromise;assert.equal(download.suggestedFilename(),'review-notes.txt');assert.equal(await readFile(await download.path(),'utf8'),'Workspace browser fixture notes');
 await snapshot('chat-desktop');await noOverflow('desktop chat');await page.getByRole('button',{name:'Archive conversation',exact:true}).click();await page.getByText('This conversation is archived. Its history and files remain available.',{exact:true}).waitFor();assert.equal(await page.locator('textarea[name=message]').count(),0);await page.getByRole('button',{name:'Reopen conversation',exact:true}).click();await page.locator('textarea[name=message]').waitFor();
 for(const width of [390,768]){await page.setViewportSize({width,height:844});for(const route of ['work','reports','chat']){await page.goto(base+'/'+route);if(route==='work')await page.getByRole('heading',{name:'Give every task a next step.'}).waitFor();if(route==='reports')await page.locator('textarea[name=completed]').waitFor();if(route==='chat'){await engineering();await page.locator('textarea[name=message]').waitFor();}await noOverflow(width+' '+route);if(width===390)await snapshot(route+'-mobile');}}
 await signIn('employee');await page.goto(base+'/work');await page.getByRole('heading',{name:'Give every task a next step.'}).waitFor();assert.equal(await page.locator('.assignment-panel').count(),0);
 await page.goto(base+'/chat');await engineering();await page.getByText(messageName,{exact:true}).waitFor();assert.equal(await page.locator('.pin-button').count(),0);
 await signIn('finance');await page.goto(base+'/chat');await page.getByRole('button',{name:'Finance · browser fixture Department',exact:true}).waitFor();assert.equal(await page.getByRole('button',{name:'Engineering · browser fixture Department',exact:true}).count(),0);assert.deepEqual(errors,[]);
 console.log('PASS: persisted tasks, assignment, report upsert, chat search/pins/history/files/archive, employee scopes, Space Grotesk, desktop/tablet/mobile overflow and no browser errors.');
}finally{await browser.close();}
