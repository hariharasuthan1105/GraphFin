import { test, expect } from '@playwright/test';
test('final narrow viewports and keyboard navigation', async ({page}) => {
  for (const width of [360,430]) {
    await page.setViewportSize({width,height:900});
    await page.goto('#/overview');
    await expect(page.getByText('84 method evaluations')).toBeVisible();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await page.screenshot({path:`../../../work/phase8/visual-production/final-${width}.png`,fullPage:true,animations:'disabled'});
    await page.getByRole('button',{name:'Toggle navigation'}).click();
    await expect(page.getByRole('navigation',{name:'Research navigation'})).toBeVisible();
    await page.screenshot({path:`../../../work/phase8/visual-production/menu-${width}.png`,animations:'disabled'});
    await page.getByRole('link',{name:/Datasets/}).focus();
    await page.keyboard.press('Escape');
    await expect(page.getByRole('button',{name:'Toggle navigation'})).toBeFocused();
  }
});
