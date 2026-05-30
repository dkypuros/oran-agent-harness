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
const riskyActionType = 'gnb_initial_ue_message'
const actionIdPattern = /python-ran-[a-f0-9]+/

async function main() {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage()

  try {
    await page.goto(appUrl, { waitUntil: 'domcontentloaded', timeout: 30000 })
    await page.waitForSelector('text=Python RAN Actions', { timeout: 20000 })

    const selectTrigger = page
      .getByText('Run python RAN action')
      .locator('xpath=following::button[1]')
    await selectTrigger.click()
    await page.getByRole('option', { name: riskyActionType, exact: true }).click()

    const runActionButton = page.getByRole('button', { name: 'Run Action' })
    await page.waitForFunction(() => {
      const button = Array.from(document.querySelectorAll('button')).find((node) =>
        node.textContent?.includes('Run Action')
      )
      return Boolean(button) && !button.hasAttribute('disabled')
    }, { timeout: 20000 })

    const beforeText = await page.locator('body').innerText()
    const beforeActionId = beforeText.match(actionIdPattern)?.[0] ?? null

    await runActionButton.click()

    await page.waitForFunction(
      ({ pattern, previousActionId }) => {
        const bodyText = document.body?.innerText ?? ''
        const match = bodyText.match(new RegExp(pattern))
        const currentActionId = match ? match[0] : null
        return (
          Boolean(currentActionId) &&
          currentActionId !== previousActionId &&
          bodyText.includes('submitted')
        )
      },
      { pattern: actionIdPattern.source, previousActionId: beforeActionId },
      { timeout: 20000 }
    )

    const midText = await page.locator('body').innerText()
    const pendingActionId = midText.match(actionIdPattern)?.[0] ?? null

    const approveButton = page.getByRole('button', { name: 'Approve Latest' })
    await page.waitForFunction(() => {
      const button = Array.from(document.querySelectorAll('button')).find((node) =>
        node.textContent?.includes('Approve Latest')
      )
      return Boolean(button) && !button.hasAttribute('disabled')
    }, { timeout: 20000 })

    await approveButton.click()

    await page.waitForFunction(
      ({ pendingId }) => {
        const bodyText = document.body?.innerText ?? ''
        return (
          bodyText.includes(pendingId) &&
          !bodyText.includes('Approving...') &&
          (bodyText.includes('failed') || bodyText.includes('completed')) &&
          bodyText.includes('Approved by dashboard-operator')
        )
      },
      { pendingId: pendingActionId },
      { timeout: 30000 }
    )

    await page.waitForTimeout(1000)
    const afterText = await page.locator('body').innerText()

    const result = {
      appUrl,
      beforeActionId,
      pendingActionId,
      stillShowingPendingId: afterText.includes(pendingActionId ?? ''),
      showsSubmitted: afterText.includes('submitted'),
      showsFailed: afterText.includes('failed'),
      showsCompleted: afterText.includes('completed'),
      showsApprovedByOperator: afterText.includes('Approved by dashboard-operator'),
      showsActionType: afterText.includes(riskyActionType),
    }

    console.log(JSON.stringify(result, null, 2))

    if (!result.pendingActionId) {
      throw new Error('Did not capture a pending python RAN action id before approval.')
    }
    if (!result.showsApprovedByOperator) {
      throw new Error('Approve Latest did not produce visible approved-by state.')
    }
    if (!(result.showsFailed || result.showsCompleted)) {
      throw new Error('Approve Latest did not produce a visible terminal state.')
    }
  } finally {
    await browser.close()
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error))
  process.exit(1)
})
