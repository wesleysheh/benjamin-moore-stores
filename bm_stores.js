const { chromium } = require('playwright');

const states = [
  { name: 'Arizona', search: 'Phoenix, AZ' },
  { name: 'Arizona', search: 'Tucson, AZ' },
  { name: 'Arizona', search: 'Flagstaff, AZ' },
  { name: 'Colorado', search: 'Denver, CO' },
  { name: 'Colorado', search: 'Colorado Springs, CO' },
  { name: 'Colorado', search: 'Grand Junction, CO' },
  { name: 'Idaho', search: 'Boise, ID' },
  { name: 'Idaho', search: 'Idaho Falls, ID' },
  { name: 'Montana', search: 'Billings, MT' },
  { name: 'Montana', search: 'Missoula, MT' },
  { name: 'Nevada', search: 'Las Vegas, NV' },
  { name: 'Nevada', search: 'Reno, NV' },
  { name: 'New Mexico', search: 'Albuquerque, NM' },
  { name: 'New Mexico', search: 'Santa Fe, NM' },
  { name: 'Utah', search: 'Salt Lake City, UT' },
  { name: 'Utah', search: 'St George, UT' },
  { name: 'Wyoming', search: 'Cheyenne, WY' },
  { name: 'Wyoming', search: 'Casper, WY' },
  { name: 'California', search: 'Los Angeles, CA' },
  { name: 'California', search: 'San Francisco, CA' },
  { name: 'California', search: 'San Diego, CA' },
  { name: 'California', search: 'Sacramento, CA' },
  { name: 'California', search: 'Fresno, CA' },
  { name: 'California', search: 'Redding, CA' },
];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  
  const allStores = new Map(); // dedupe by store name+address
  
  for (const loc of states) {
    const page = await context.newPage();
    
    // Intercept API responses
    const stores = [];
    page.on('response', async (response) => {
      const url = response.url();
      if (url.includes('store') && url.includes('api') || url.includes('dealer') || url.includes('locator') && response.status() === 200) {
        try {
          const text = await response.text();
          if (text.includes('{') && text.length > 100) {
            stores.push({ url, body: text });
          }
        } catch(e) {}
      }
    });
    
    try {
      await page.goto('https://www.benjaminmoore.com/en-us/store-locator', { waitUntil: 'networkidle', timeout: 15000 });
    } catch(e) {
      // ok if timeout, page may still work
    }
    
    // Try to dismiss cookie banner
    try {
      await page.click('button:has-text("Accept Cookies")', { timeout: 3000 });
    } catch(e) {}
    
    // Fill search
    try {
      const input = page.locator('input[placeholder*="Address"]');
      await input.fill(loc.search);
      await page.click('button:has-text("Search Address")');
      await page.waitForTimeout(5000);
      
      // Check captured responses
      if (stores.length > 0) {
        console.error(`[${loc.search}] Captured ${stores.length} API responses`);
        for (const s of stores) {
          console.error(`  URL: ${s.url.substring(0, 200)}`);
          console.log(s.body);
        }
      } else {
        // Try to read results from DOM
        console.error(`[${loc.search}] No API intercepts, reading DOM...`);
        const results = await page.locator('[class*="store"], [class*="dealer"], [class*="result"], [data-testid*="store"]').allTextContents();
        console.error(`  Found ${results.length} DOM elements`);
        for (const r of results) {
          console.log(`DOM|${loc.search}|${r.replace(/\n/g, ' ').trim()}`);
        }
      }
    } catch(e) {
      console.error(`[${loc.search}] Error: ${e.message}`);
    }
    
    await page.close();
  }
  
  await browser.close();
})();
