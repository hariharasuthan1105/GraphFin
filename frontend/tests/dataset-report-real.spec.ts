import {test,expect} from '@playwright/test';
import {mkdirSync,readFileSync,writeFileSync} from 'node:fs';
test('real PDF download for each approved dataset',async({page})=>{
  const folder='../../../work/pdf-reports/browser-downloads';mkdirSync(folder,{recursive:true});
  const observations:unknown[]=[];
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('#/datasets');
  for(const [id,name] of [['ibm-5k','IBM AML 5k'],['ibm-50k','IBM AML 50k'],['paysim','PaySim']]){
    await page.getByRole('button',{name,exact:true}).click();
    const button=page.getByRole('button',{name:'Download Dataset Report (PDF)'});await expect(button).toBeVisible();
    const start=Date.now();const pending=page.waitForEvent('download');await button.click();const download=await pending;
    expect(download.suggestedFilename()).toBe(`GraphFin_${id}_dataset_report.pdf`);
    const path=folder+'/'+download.suggestedFilename();await download.saveAs(path);const bytes=readFileSync(path);
    expect(bytes.subarray(0,5).toString()).toBe('%PDF-');expect((bytes.toString('latin1').match(/\/Type\s*\/Page\b/g)||[]).length).toBe(4);
    observations.push({dataset:id,bytes:bytes.length,downloadMs:Date.now()-start});
  }
  await page.screenshot({path:'../../../work/pdf-reports/dataset-download-desktop.png',fullPage:true,animations:'disabled'});
  await page.setViewportSize({width:430,height:950});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:'../../../work/pdf-reports/dataset-download-mobile.png',fullPage:true,animations:'disabled'});
  expect(errors).toEqual([]);writeFileSync('../../../work/pdf-reports/real-downloads.json',JSON.stringify({observations,errors},null,2));
});
