function loadPlaywright() {
  const candidates = [
    process.env.PLAYWRIGHT_NODE_PATH,
    'playwright',
    '/Users/davidkypuros/.npm-global/lib/node_modules/playwright',
  ].filter(Boolean)

  for (const candidate of candidates) {
    try {
      return require(candidate)
    } catch {
      // try next candidate
    }
  }

  throw new Error(
    'Unable to load playwright. Set PLAYWRIGHT_NODE_PATH or install playwright locally.'
  )
}

const { chromium } = loadPlaywright()
const appUrl = process.env.APP_URL ?? 'http://127.0.0.1:3000'

async function main() {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage()
  const actionIdPattern = /ocudu-[a-f0-9]+/

  try {
    await page.goto(appUrl, { waitUntil: 'domcontentloaded', timeout: 30000 })
    await page.waitForSelector('text=OCUDU Integration', { timeout: 20000 })
    await page.waitForFunction(() => {
      const bodyText = document.body?.innerText ?? ''
      return (
        bodyText.includes('OCUDU Integration') &&
        bodyText.includes('Integration Role') &&
        bodyText.includes('Libraries') &&
        bodyText.includes('Next step')
      )
    }, { timeout: 20000 })
    await page.waitForFunction(() => {
      const bodyText = document.body?.innerText ?? ''
      return (
        bodyText.includes('Checkout Present') &&
        bodyText.includes('local-source-checkout') &&
        bodyText.includes('Build an OCUDU runtime/control adapter')
      )
    }, { timeout: 20000 })

    const runButton = page.getByRole('button', { name: 'Run OCUDU Action' })
    const beforeText = await page.locator('body').innerText()
    const beforeActionId = beforeText.match(actionIdPattern)?.[0] ?? null
    await runButton.click()
    await page.waitForFunction(
      ({ pattern, previousActionId }) => {
        const bodyText = document.body?.innerText ?? ''
        const match = bodyText.match(new RegExp(pattern))
        const currentActionId = match ? match[0] : null
        return (
          Boolean(currentActionId) &&
          currentActionId !== previousActionId &&
          bodyText.includes('completed')
        )
      },
      { pattern: actionIdPattern.source, previousActionId: beforeActionId },
      { timeout: 20000 }
    )

    const text = await page.locator('body').innerText()
    const afterActionId = text.match(actionIdPattern)?.[0] ?? null
    const result = {
      appUrl,
      hasOcuduPanel: text.includes('OCUDU Integration'),
      hasIntegrationRole: text.includes('Integration Role'),
      hasLibraries: text.includes('Libraries'),
      hasNextStep: text.includes('Next step'),
      showsCheckoutPresent: text.includes('Checkout Present'),
      showsLocalSourceCheckout: text.includes('local-source-checkout'),
      showsBuildAdapterStep: text.includes('Build an OCUDU runtime/control adapter'),
      beforeActionId,
      afterActionId,
      actionChanged: Boolean(afterActionId) && afterActionId !== beforeActionId,
      showsCompleted: text.includes('completed'),
    }

    console.log(JSON.stringify(result, null, 2))

    if (!result.hasOcuduPanel || !result.hasIntegrationRole || !result.hasLibraries || !result.hasNextStep) {
      throw new Error('OCUDU panel did not render the expected parity fields.')
    }
    if (!result.showsCheckoutPresent || !result.showsLocalSourceCheckout || !result.showsBuildAdapterStep) {
      throw new Error('OCUDU panel did not surface the expected live OCUDU context values.')
    }
    if (!result.actionChanged || !result.showsCompleted) {
      throw new Error('OCUDU panel did not surface a visible OCUDU action lifecycle update.')
    }
  } finally {
    await browser.close()
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error))
  process.exit(1)
})
