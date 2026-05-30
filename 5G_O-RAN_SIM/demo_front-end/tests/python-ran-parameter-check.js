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

async function selectAction(page, actionType) {
  const trigger = page
    .getByText('Run python RAN action')
    .locator('xpath=following::button[1]')
  await trigger.click()
  await page.getByRole('option', { name: actionType, exact: true }).click()
  await page.waitForTimeout(300)
}

async function main() {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage()

  try {
    await page.goto(appUrl, { waitUntil: 'domcontentloaded', timeout: 30000 })
    await page.waitForSelector('text=Python RAN Actions', { timeout: 20000 })
    await page.waitForFunction(() => {
      const bodyText = document.body?.innerText ?? ''
      return bodyText.includes('Run Action') && bodyText.includes('Approve Latest')
    }, { timeout: 20000 })

    await selectAction(page, 'collect_logs')
    const hasLogLimit = await page.getByLabel('Log limit').isVisible()

    await selectAction(page, 'gnb_initial_ue_message')
    const hasNasPdu = await page.getByLabel('NAS PDU').isVisible()

    await selectAction(page, 'du_initial_ul_rrc_message')
    const hasRrcContainer = await page.getByLabel('RRC container').isVisible()

    await selectAction(page, 'cu_create_rrc_setup')
    const hasRrcTransactionId = await page.getByLabel('RRC transaction id').isVisible()
    const hasGnbDuUeId = await page.getByLabel('gNB-DU UE F1AP id').isVisible()

    await selectAction(page, 'du_process_prach')
    const hasPrachIndex = await page.getByLabel('PRACH preamble index').isVisible()

    const result = {
      appUrl,
      hasLogLimit,
      hasNasPdu,
      hasRrcContainer,
      hasRrcTransactionId,
      hasGnbDuUeId,
      hasPrachIndex,
    }

    console.log(JSON.stringify(result, null, 2))

    if (!hasLogLimit || !hasNasPdu || !hasRrcContainer || !hasRrcTransactionId || !hasGnbDuUeId || !hasPrachIndex) {
      throw new Error('One or more Python RAN parameter forms did not render as expected.')
    }
  } finally {
    await browser.close()
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error))
  process.exit(1)
})
