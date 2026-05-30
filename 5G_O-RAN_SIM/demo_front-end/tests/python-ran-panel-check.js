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
const expectedHeading = 'Python RAN Actions'
const actionIdPattern = /python-ran-[a-f0-9]+/

async function main() {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage()

  try {
    await page.goto(appUrl, { waitUntil: 'domcontentloaded', timeout: 30000 })
    await page.waitForSelector(`text=${expectedHeading}`, { timeout: 20000 })
    const runActionButton = page.getByRole('button', { name: 'Run Action' })
    await page.waitForFunction(() => {
      const button = Array.from(document.querySelectorAll('button')).find((node) =>
        node.textContent?.includes('Run Action')
      )
      return Boolean(button) && !button.hasAttribute('disabled')
    }, { timeout: 20000 })
    await page.waitForTimeout(1000)

    const beforeText = await page.locator('body').innerText()
    const beforeActionId = beforeText.match(actionIdPattern)?.[0] ?? null

    await runActionButton.click()

    await page.waitForFunction(
      ({ pattern, previousActionId }) => {
        const bodyText = document.body?.innerText ?? ''
        const match = bodyText.match(new RegExp(pattern))
        const currentActionId = match ? match[0] : null
        return Boolean(currentActionId) && currentActionId !== previousActionId
      },
      { pattern: actionIdPattern.source, previousActionId: beforeActionId },
      { timeout: 20000 }
    )

    await page.waitForTimeout(1500)
    const afterText = await page.locator('body').innerText()
    const afterActionId = afterText.match(actionIdPattern)?.[0] ?? null

    const result = {
      appUrl,
      hasPanel: afterText.includes('Python RAN Actions'),
      hasSupportedActions: afterText.includes('Supported Actions'),
      hasLatestAction: afterText.includes('Latest action'),
      beforeActionId,
      afterActionId,
      actionChanged: Boolean(afterActionId) && afterActionId !== beforeActionId,
      showsCompleted: afterText.includes('completed'),
      showsSubmitted: afterText.includes('submitted'),
      showsPassed: afterText.includes('passed'),
      showsPending: afterText.includes('pending'),
    }

    console.log(JSON.stringify(result, null, 2))

    if (!result.hasPanel || !result.hasSupportedActions || !result.hasLatestAction) {
      throw new Error('Python RAN panel did not render expected sections.')
    }

    if (!result.actionChanged) {
      throw new Error('Run Action did not produce a visible latest-action id change.')
    }

    if (!(result.showsCompleted || result.showsSubmitted)) {
      throw new Error('Run Action did not produce a visible action status.')
    }
  } finally {
    await browser.close()
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error))
  process.exit(1)
})
