"""Runtime DOM behavior using a minimal DOM adapter; not a visual browser test."""
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class CompanyBoxTests(unittest.TestCase):
    def test_generated_button_navigates_and_moves_same_conversation_without_execution(self):
        if not shutil.which('node'): self.skipTest('Node unavailable')
        html=Path(__file__).with_name('panel.html').read_text()
        script=re.search(r'<script>(.*?)</script>',html,re.S)[1]
        harness=r'''
const vm=require('node:vm'),assert=require('node:assert/strict');
class Element{
 constructor(tag='div'){this.tagName=tag;this.children=[];this.dataset={};this.hidden=false;this.value='';this.textContent='';this.classList={add(){},remove(){}}}
 append(...items){for(let x of items){if(x.parentElement)x.remove();x.parentElement=this;this.children.push(x)}}
 replaceChildren(...items){this.children.forEach(x=>x.parentElement=null);this.children=[];this.append(...items)}
 remove(){if(this.parentElement){let p=this.parentElement;p.children=p.children.filter(x=>x!==this);this.parentElement=null}}
 addEventListener(){} setAttribute(k,v){this[k]=v} scrollIntoView(){}
 querySelectorAll(selector){let key=selector.slice(1,-1).replace('data-','').replace(/-([a-z])/g,(_,x)=>x.toUpperCase());return this.children.flatMap(x=>[...(key in x.dataset?[x]:[]),...x.querySelectorAll(selector)])}
}
let ids={},nodes=[];
for(let match of HTML.matchAll(/<([a-z]+)([^>]*?)>/g)){let e=new Element(match[1]);let attrs=match[2];for(let a of attrs.matchAll(/([\w-]+)="([^"]*)"/g)){if(a[1]==='id')ids[a[2]]=e;else if(a[1].startsWith('data-'))e.dataset[a[1].slice(5).replace(/-([a-z])/g,(_,x)=>x.toUpperCase())]=a[2]}e.hidden=/\bhidden\b/.test(attrs);nodes.push(e)}
ids.setupHome.append(ids.setupShell);
const document={getElementById:id=>ids[id],createElement:tag=>new Element(tag),addEventListener(){},querySelectorAll:sel=>{let key=sel.slice(1,-1).slice(5);return nodes.filter(x=>key in x.dataset)},querySelector:sel=>{let m=sel.match(/data-view="(.*?)"/);return nodes.find(x=>x.dataset.view===m[1])}};
let network=0;
const ctx={document,window:{addEventListener(){}},navigator:{},crypto:{randomUUID:()=> 'fake-id'},console,TextEncoder,setInterval(){},clearInterval(){},setTimeout(){},clearTimeout(){},fetch(){network++;throw Error('unexpected network')},localStorage:{},confirm(){return false},URL};
vm.createContext(ctx);vm.runInContext(SCRIPT,ctx);
vm.runInContext(`el('workspace').hidden=false;token='fake-owner';setupRender({revision:2,updated_at:'2026-10-11T13:00:00Z',mode:'ai',state:'draft',missing:[],profile:{business_name:'Aurora',segment:'jardim',offer:'poda',products:[{name:'poda',description:'jardim'}]},messages:[{role:'user',text:'Quero ver retornos'},{role:'assistant',text:'Você pode conferir os retornos por aqui.'}],suggestions:['Quero editar meus preços'],actions:[{area:'tasks',label:'Conferir retornos'},{area:'contact_call',label:'Ligar para o responsável',href:'tel:+5511999999999'}]})`,ctx);
(async()=>{
 assert.equal(ids.setupActions.children[0].tagName,'button');
 assert.equal(ids.setupActions.children[1].tagName,'a');
 assert.equal(ids.setupActions.children[1].href,'tel:+5511999999999');
 assert.equal(ids.setupActions.children[1].textContent,'Ligar para o responsável');
 assert.equal(ids.setupActions.children[0].children[0].className,'preset-icon');
 assert.equal(ids.setupActions.children[1].children.length,1);
 assert.equal(ids.setupChat.children.length,2);
 const shell=ids.setupShell;await ids.setupActions.children[0].onclick();
 assert.equal(shell.parentElement,ids.setupFloatBody);assert.equal(ids.setupFloating.hidden,false);
 assert.equal(nodes.find(x=>x.dataset.section==='tasks').hidden,false);
 assert.equal(ids.setupChat.children.length,2);assert.equal(network,0);
 ids.setupMinimize.onclick();assert.equal(ids.setupFloating.hidden,true);assert.equal(ids.setupDock.hidden,false);
 ids.setupExpand.onclick();assert.equal(shell.parentElement,ids.setupHome);assert.equal(ids.setupHome.hidden,false);
 assert.equal(ids.setupChat.children.length,2);assert.equal(network,0);
 console.log('dynamic buttons, hidden destinations and same floating conversation verified');
})().catch(e=>{console.error(e);process.exitCode=1});
'''
        import json
        content='const HTML='+json.dumps(html)+';const SCRIPT='+json.dumps(script)+';\n'+harness
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'company-box.js';path.write_text(content)
            result=subprocess.run(['node',str(path)],text=True,capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__':unittest.main()
