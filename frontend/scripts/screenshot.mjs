import { chromium } from 'playwright'

const outDir = process.env.OUT_DIR ?? '.'
const browser = await chromium.launch()

async function shot(name, { dark = false, actions } = {}) {
  const ctx = await browser.newContext({
    viewport: { width: 1100, height: 900 },
    colorScheme: dark ? 'dark' : 'light',
  })
  const page = await ctx.newPage()
  page.on('console', (m) => m.type() === 'error' && console.log('CONSOLE ERROR:', m.text()))
  page.on('pageerror', (e) => console.log('PAGE ERROR:', e.message))
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' })
  if (actions) await actions(page)
  await page.screenshot({ path: `${outDir}/${name}.png`, fullPage: true })
  await ctx.close()
  console.log(`saved ${name}.png`)
}

await shot('01-dashboard')
await shot('02-predict', {
  actions: async (page) => {
    await page.getByRole('button', { name: 'Predict', exact: true }).first().click() // tab
    await page.getByRole('button', { name: 'Predict', exact: true }).last().click() // run
    await page.waitForSelector('text=Analyst summary', { timeout: 60000 })
  },
})
await shot('03-simulate', {
  actions: async (page) => {
    await page.getByRole('button', { name: 'Simulate', exact: true }).click()
    await page.getByRole('button', { name: 'Simulate tournament' }).click()
    await page.waitForSelector('text=Championship probability', { timeout: 120000 })
  },
})
await shot('04-chat', {
  actions: async (page) => {
    await page.getByRole('button', { name: 'Analyst Chat' }).click()
    await page.getByRole('button', { name: 'Predict BRA vs ARG' }).click()
    await page.waitForTimeout(8000)
  },
})
await shot('05-dashboard-dark', { dark: true })
await shot('06-simulate-dark', {
  dark: true,
  actions: async (page) => {
    await page.getByRole('button', { name: 'Simulate', exact: true }).click()
    await page.getByRole('button', { name: 'Simulate tournament' }).click()
    await page.waitForSelector('text=Championship probability', { timeout: 120000 })
  },
})

await browser.close()
