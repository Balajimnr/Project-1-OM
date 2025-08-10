import asyncio
from playwright.async_api import async_playwright, expect
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Get the absolute path to the HTML file
        html_file_path = os.path.abspath('simulator.html')
        await page.goto(f'file://{html_file_path}')
        await page.wait_for_load_state('networkidle')

        # --- 1. SETUP ---
        # a. Sydney creates AUD liquidity and sends it to London for the repay test
        await page.select_option('select#tokenizeParticipant', 'Sydney')
        await page.select_option('select#tokenizeCurrency', 'AUD')
        await page.fill('input#tokenizeAmount', '100000')
        await page.locator('div[aria-label="Tokenize funds"] button:has-text("Go")').click()
        await page.wait_for_selector('#statusModalOverlay')
        await page.wait_for_selector('#statusModalOverlay', state='hidden', timeout=60000)

        await page.select_option('select#sender', 'Sydney')
        await page.select_option('select#receiver', 'London')
        await page.select_option('select#transferCurrency', 'AUD')
        await page.fill('input#transferAmount', '100000')
        await page.locator('div[aria-label="Transfer tokens"] button:has-text("Go")').click()
        await page.wait_for_selector('#statusModalOverlay')
        await page.wait_for_selector('#statusModalOverlay', state='hidden', timeout=60000)

        # b. Dubai gets 500,000 USD to create a borrowable liquidity pool
        await page.select_option('select#tokenizeParticipant', 'Dubai')
        await page.select_option('select#tokenizeCurrency', 'USD')
        await page.fill('input#tokenizeAmount', '500000')
        await page.locator('div[aria-label="Tokenize funds"] button:has-text("Go")').click()
        await page.wait_for_selector('#statusModalOverlay')
        await page.wait_for_selector('#statusModalOverlay', state='hidden', timeout=60000)

        # c. London borrows 20,000 USD by transferring to New York
        await page.select_option('select#sender', 'London')
        await page.select_option('select#receiver', 'New York')
        await page.select_option('select#transferCurrency', 'USD')
        await page.fill('input#transferAmount', '20000')

        # This should trigger a swap first, which we decline, then borrow, which we accept.
        async def handle_borrow_dialogs(dialog):
            if "borrow" in dialog.message.lower():
                await dialog.accept()
            else:
                await dialog.dismiss()
        page.on('dialog', handle_borrow_dialogs)
        await page.locator('div[aria-label="Transfer tokens"] button:has-text("Go")').click()
        await page.wait_for_selector('#statusModalOverlay')
        await page.wait_for_selector('#statusModalOverlay', state='hidden', timeout=60000)
        page.remove_listener('dialog', handle_borrow_dialogs)

        await page.screenshot(path='jules-scratch/verification/01_setup_complete.png', full_page=True)

        # --- 2. TEST CASE: Smart Repay (Accept Swap) ---
        await page.select_option('select#repayParticipant', 'London')
        await page.select_option('select#repayCurrency', 'USD')

        # Wait for the loan dropdown to be populated
        await page.wait_for_function("document.getElementById('repayLoanId').options.length > 0 && document.getElementById('repayLoanId').options[0].value !== 'No outstanding loans'")

        # The amount to repay is the full loan amount
        await page.fill('input#repayAmount', '20000')

        # Expect a swap confirmation, which we accept
        page.once('dialog', lambda dialog: asyncio.create_task(dialog.accept()))
        await page.locator('div[aria-label="Repay borrowed funds"] button:has-text("Go")').click()
        await page.wait_for_selector('#statusModalOverlay')
        await page.wait_for_selector('#statusModalOverlay', state='hidden', timeout=60000)

        await page.screenshot(path='jules-scratch/verification/02_after_smart_repay.png', full_page=True)

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
