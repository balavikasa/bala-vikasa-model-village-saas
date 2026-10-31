"""Executable UI regression suite for Admin Master Data. Run with: python tests/browser_admin_master_data.py"""
from __future__ import annotations

import asyncio
from pathlib import Path
from jinja2 import Environment, DictLoader
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = "<!doctype html><html><head><meta charset='utf-8'><style>.hidden{display:none!important}</style></head><body>{% block content %}{% endblock %}{% block scripts %}{% endblock %}</body></html>"
MACROS = "{% macro icon(name) %}<span></span>{% endmacro %}{% macro slogan() %}<span></span>{% endmacro %}"

def html():
    env = Environment(loader=DictLoader({
        'base.html': BASE,
        'components/reference_ui.html': MACROS,
        'admin.html': (ROOT / 'app/templates/admin.html').read_text(),
    }))
    env.globals['url_for'] = lambda endpoint, **kw: '/admin' if endpoint=='pages.admin' else '/other'
    return env.get_template('admin.html').render()

# This fixture mirrors the real JSON contract, not internal JS state.
SCRIPT = """(() => {
const definitions={
  pms:{label:'Program Managers',fields:[{name:'full_name',type:'text',required:true},{name:'email',type:'email'},{name:'mobile',type:'tel'},{name:'is_enabled',type:'boolean'}],columns:['id','full_name']},
  pcs:{label:'Project Coordinators',fields:[{name:'full_name',type:'text',required:true},{name:'cluster',type:'select',required:true,choices:['CSRB','PDTC']},{name:'pm_id',type:'relationship',required:false,related_resource:'pms'},{name:'email',type:'email'},{name:'mobile',type:'tel'},{name:'is_enabled',type:'boolean'}],columns:['id','full_name']},
  das:{label:'Development Agents',fields:[{name:'full_name',type:'text',required:true},{name:'pc_id',type:'relationship',required:true,related_resource:'pcs'},{name:'email',type:'email'},{name:'mobile',type:'tel'},{name:'is_enabled',type:'boolean'}],columns:['id','full_name']},
  villages:{label:'Villages',fields:[{name:'name',type:'text',required:true},{name:'da_id',type:'relationship',required:true,related_resource:'das'},{name:'is_enabled',type:'boolean'}],columns:['id','name']},
  committees:{label:'Committees',fields:[{name:'name',type:'text',required:true},{name:'village_id',type:'relationship',required:true,related_resource:'villages'},{name:'is_enabled',type:'boolean'}],columns:['id','name']},
  'committee-members':{label:'Committee Members',fields:[{name:'full_name',type:'text',required:true},{name:'committee_id',type:'relationship',required:true,related_resource:'committees'},{name:'is_enabled',type:'boolean'}],columns:['id','full_name']},
  users:{label:'Users',fields:[{name:'display_name',type:'text',required:true},{name:'role',type:'select',required:true,choices:['admin','pm','pc','da']},{name:'email',type:'email'},{name:'mobile',type:'tel'},{name:'pm_id',type:'relationship',related_resource:'pms'},{name:'pc_id',type:'relationship',related_resource:'pcs'},{name:'da_id',type:'relationship',related_resource:'das'},{name:'password',type:'password'},{name:'is_enabled',type:'boolean'}],columns:['id','display_name']},
};
const items={pms:[{id:1,full_name:'Program Manager 1'}],pcs:[{id:2,full_name:'PC A',cluster:'PDTC'},{id:3,full_name:'PC B',cluster:'CSRB'}],das:[{id:4,full_name:'DA A'},{id:5,full_name:'DA B'}],villages:[{id:6,name:'Village A',mandal:'Narsampet',district:'Warangal'},{id:7,name:'Village B',mandal:'Parkal',district:'Warangal'}],committees:[{id:8,name:'Water',village_name:'Village A'},{id:9,name:'Water',village_name:'Village B'}],users:[], 'committee-members':[]};
window.__apiCalls=[];
window.BVUI={icon:()=>''};
window.MV={toast:()=>{},api:async(url,opts={})=>{
 const u=new URL(url,'https://example.org');const seg=u.pathname.split('/');const slug=seg[4];const method=opts.method||'GET';
 if(method==='POST'||method==='PATCH'){
   const body=JSON.parse(opts.body||'{}');window.__apiCalls.push({slug,method,body});
   return {ok:true,status:201,json:async()=>({item:{id:100, ...body}})};
 }
 if(u.pathname.endsWith('/resources'))return {ok:true,status:200,json:async()=>({resources:definitions})};
 if(method==='GET'){
   const array=items[slug]||[]; const page=Number(u.searchParams.get('page')||1); const per=Number(u.searchParams.get('per_page')||25);
   const rows=array.slice((page-1)*per,page*per);
   return {ok:true,status:200,json:async()=>({items:rows,total:array.length,page})};
 }
 return {ok:false,status:400,json:async()=>({error:'not available'})};
}}
})();"""

async def run():
    async with async_playwright() as play:
        browser = await play.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page=await browser.new_page(viewport={'width':1280,'height':900})
        page.set_default_timeout(4500)
        page.on("pageerror",lambda e: print("PAGEERROR", str(e), flush=True))
        await page.set_content(html())
        await page.add_script_tag(content=SCRIPT)
        await page.add_script_tag(path=str(ROOT / 'app/static/js/admin.js'))
        await page.wait_for_function("document.querySelector('#admin-resource').options.length > 0")
        print('Loaded current Admin Master Data UI')
        print('step PC form',flush=True)
        # Test 1: full PC->PM assignment option and search at the creation boundary.
        await page.select_option('#admin-resource', 'pcs')
        await page.click('#admin-add')
        assert await page.locator('#admin-dialog').evaluate('(e)=>e.open')
        assert await page.locator('#admin-field-pm_id').count() == 1
        assert await page.locator('[data-relationship-search="pm_id"]').count() == 1, 'PM lookup must be searchable'
        await page.click('#admin-dialog button[value=cancel]')
        print('step DA form',flush=True)
        # Test 2: DA staff creation can include linked sign-in, all in one transaction.
        await page.select_option('#admin-resource', 'das')
        await page.click('#admin-add')
        assert await page.locator('#admin-create-login').count()==1, 'Missing optional linked login provisioning'
        await page.fill('#admin-field-full_name', 'New DA')
        await page.select_option('#admin-field-pc_id', '2')
        await page.check('#admin-create-login')
        await page.fill('#admin-provision-email', 'newda@example.org')
        await page.fill('#admin-provision-password', 'SufficientlyStrong321')
        await page.fill('#admin-provision-confirm', 'SufficientlyStrong321')
        await page.click('#admin-save')
        await page.wait_for_function('window.__apiCalls.length > 0')
        call=await page.evaluate('window.__apiCalls.at(-1)')
        assert call['slug']=='das' and call['method']=='POST'
        assert call['body']['create_login'] is True
        assert call['body']['login_email']=='newda@example.org'
        assert call['body']['login_password']=='SufficientlyStrong321'
        print('step User form',flush=True)
        # Test 3: role-aware accounts show exactly the required profile relationship.
        await page.select_option('#admin-resource', 'users')
        await page.click('#admin-add')
        assert await page.locator('#admin-field-role').input_value() == '', 'Never preselect Administrator role for a new user'
        await page.select_option('#admin-field-role', 'da')
        assert await page.locator('#admin-field-da_id').is_visible()
        assert not await page.locator('#admin-field-pm_id').is_visible()
        assert not await page.locator('#admin-field-pc_id').is_visible()
        print('step Committee form',flush=True)
        # Test 4: committee names are disambiguated by village so assignment is safe.
        await page.click('#admin-dialog button[value=cancel]')
        await page.select_option('#admin-resource','committee-members')
        await page.click('#admin-add')
        values=await page.locator('#admin-field-committee_id option').all_text_contents()
        assert any('Village A' in label for label in values) and any('Village B' in label for label in values)
        # Test 5: an already-created staff profile can receive login access later.
        await page.click('#admin-dialog button[value=cancel]')
        await page.select_option('#admin-resource','das')
        await page.locator('[data-edit="4"]').click()
        assert await page.locator('#admin-login-provision').is_visible(), 'Admin must be able to provision an existing DA'
        print('PASS: PC->PM, DA+login, role-aware Users, committee assignment, existing staff')
        await browser.close()

if __name__=='__main__':
    asyncio.run(run())
