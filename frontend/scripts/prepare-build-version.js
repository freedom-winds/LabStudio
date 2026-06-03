import { readFile, writeFile } from 'node:fs/promises'
import { createInterface } from 'node:readline/promises'
import { stdin as input, stdout as output } from 'node:process'

const VERSION_PATTERN = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$/

async function readJson(path) {
  return JSON.parse(await readFile(path, 'utf8'))
}

async function writeJson(path, data) {
  await writeFile(path, `${JSON.stringify(data, null, 2)}\n`, 'utf8')
}

const packageJsonPath = new URL('../package.json', import.meta.url)
const packageLockPath = new URL('../package-lock.json', import.meta.url)
const versionJsonPath = new URL('../src/version.json', import.meta.url)

const packageJson = await readJson(packageJsonPath)
const currentVersion = packageJson.version

const rl = createInterface({ input, output })
console.log(`当前系统版本号：v${currentVersion}`)
const nextVersion = (await rl.question('请输入更新后的新版本号：')).trim()
rl.close()

if (!nextVersion) {
  console.error('构建已取消：必须输入新的版本号。')
  process.exit(1)
}

if (!VERSION_PATTERN.test(nextVersion)) {
  console.error('构建已取消：版本号格式应类似 1.2.3、1.2.3-beta.1。')
  process.exit(1)
}

if (nextVersion === currentVersion) {
  console.error('构建已取消：新版本号不能与当前版本号相同。')
  process.exit(1)
}

packageJson.version = nextVersion
await writeJson(packageJsonPath, packageJson)

const packageLock = await readJson(packageLockPath)
packageLock.version = nextVersion
if (packageLock.packages?.['']) packageLock.packages[''].version = nextVersion
await writeJson(packageLockPath, packageLock)

await writeJson(versionJsonPath, { version: nextVersion })
console.log(`系统版本号已更新为：v${nextVersion}`)
