import { chromium } from 'playwright';

const BASE = 'http://localhost:7878';

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  // 1. Dev login as seller
  console.log('1. Logging in as seller...');
  const loginRes = await page.request.post('http://localhost:7879/api/v1/auth/dev-login', {
    data: { role: 'seller' },
    headers: { 'Content-Type': 'application/json' },
  });
  const loginData = await loginRes.json();
  console.log('   Got token, user:', loginData.first_name, loginData.last_name);

  // Set tokens in localStorage before navigating
  await page.goto(BASE);
  await page.evaluate((data) => {
    localStorage.setItem('auth_token', data.access_token);
    localStorage.setItem('auth_refresh_token', data.refresh_token);
  }, loginData);

  // 2. Navigate to seller listings page
  console.log('2. Navigating to /my-listings...');
  await page.goto(`${BASE}/my-listings`);
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: '/tmp/test-01-listings-page.png', fullPage: true });
  console.log('   Screenshot: /tmp/test-01-listings-page.png');

  // 3. Check if OLX tab/filter exists and click it
  console.log('3. Looking for OLX filter...');
  const olxTab = page.locator('button', { hasText: 'OLX' }).first();
  if (await olxTab.isVisible()) {
    await olxTab.click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: '/tmp/test-02-olx-filter.png', fullPage: true });
    console.log('   Screenshot: /tmp/test-02-olx-filter.png');
  } else {
    console.log('   OLX tab not found, checking all listings...');
  }

  // 4. Look for the 3-dot menu on OLX card
  console.log('4. Looking for OLX card menu...');
  const menuButtons = page.locator('button[aria-haspopup="menu"]');
  const menuCount = await menuButtons.count();
  console.log(`   Found ${menuCount} menu button(s)`);

  if (menuCount > 0) {
    // Find the OLX card's menu button (the last one or with loading attribute)
    await menuButtons.last().click();
    await page.waitForTimeout(300);
    await page.screenshot({ path: '/tmp/test-03-olx-menu-open.png', fullPage: true });
    console.log('   Screenshot: /tmp/test-03-olx-menu-open.png');

    // 5. Click "Edit" in the menu
    console.log('5. Clicking Edit menu item...');
    const editItem = page.locator('[role="menuitem"]', { hasText: /Tahrirlash|Редактировать|Edit/ }).first();
    if (await editItem.isVisible()) {
      // Listen for navigation
      const [response] = await Promise.all([
        page.waitForResponse((resp) => resp.url().includes('/claim-olx/'), { timeout: 10000 }).catch(() => null),
        editItem.click(),
      ]);

      if (response) {
        console.log(`   Claim API response: ${response.status()}`);
        const body = await response.json().catch(() => ({}));
        console.log(`   New listing ID: ${body.id || 'N/A'}`);
      }

      await page.waitForTimeout(2000);
      await page.screenshot({ path: '/tmp/test-04-after-claim.png', fullPage: true });
      console.log(`   Current URL: ${page.url()}`);
      console.log('   Screenshot: /tmp/test-04-after-claim.png');

      // Check if we got redirected to edit page
      if (page.url().includes('/edit/')) {
        console.log('6. Successfully redirected to edit page!');
        await page.waitForLoadState('networkidle');
        await page.screenshot({ path: '/tmp/test-05-edit-page.png', fullPage: true });
        console.log('   Screenshot: /tmp/test-05-edit-page.png');
      }
    } else {
      console.log('   Edit menu item not found');
      await page.screenshot({ path: '/tmp/test-03b-menu-contents.png', fullPage: true });
    }
  } else {
    console.log('   No menu buttons found. Taking screenshot of current state.');
    await page.screenshot({ path: '/tmp/test-03-no-menu.png', fullPage: true });
  }

  // 7. Go back to listings and verify OLX card is gone
  console.log('7. Going back to /my-listings to verify...');
  await page.goto(`${BASE}/my-listings`);
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: '/tmp/test-06-after-verify.png', fullPage: true });
  console.log('   Screenshot: /tmp/test-06-after-verify.png');

  await browser.close();
  console.log('\nDone!');
}

main().catch((e) => { console.error('Error:', e.message); process.exit(1); });
