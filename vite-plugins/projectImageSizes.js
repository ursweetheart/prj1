/* Plugin Vite: đọc kích thước thật (rộng × cao) của mọi ảnh trong một thư mục
 * (mặc định src/assets/projects) và cung cấp qua module ảo:
 *
 *   import SIZES from 'virtual:project-image-sizes'
 *   SIZES['du-an-mau-01/01-phong-khach.jpg'] // → [2048, 1463]
 *   SIZES['du-an-mau-01.jpg']                // ảnh ở gốc thư mục
 *
 * Chỉ đọc phần đầu file (JPEG / PNG / WebP), không cần thư viện ngoài.
 * Khi chạy dev: thêm / xoá / sửa ảnh trong thư mục thì trang tự tải lại. */
import fs from 'node:fs'
import path from 'node:path'

const ID = 'virtual:project-image-sizes'
const RESOLVED = '\0' + ID
const IMAGE = /\.(jpe?g|png|webp|avif)$/i

// [width, height] hoặc null nếu không đọc được
export function readImageSize(b) {
  if (b.length < 30) return null
  // PNG: chữ ký 8 byte, rồi chunk IHDR
  if (b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47) {
    return [b.readUInt32BE(16), b.readUInt32BE(20)]
  }
  // JPEG: tìm marker SOFn
  if (b[0] === 0xff && b[1] === 0xd8) {
    let i = 2
    while (i + 9 < b.length) {
      if (b[i] !== 0xff) { i++; continue }
      const m = b[i + 1]
      if (m === 0xff) { i++; continue }
      if (m === 0xd8 || m === 0x01 || (m >= 0xd0 && m <= 0xd7)) { i += 2; continue }
      const sof = m >= 0xc0 && m <= 0xcf && m !== 0xc4 && m !== 0xc8 && m !== 0xcc
      if (sof) return [b.readUInt16BE(i + 7), b.readUInt16BE(i + 5)]
      i += 2 + b.readUInt16BE(i + 2)
    }
    return null
  }
  // WebP: RIFF....WEBP + chunk VP8 / VP8L / VP8X
  if (b.toString('ascii', 0, 4) === 'RIFF' && b.toString('ascii', 8, 12) === 'WEBP') {
    const chunk = b.toString('ascii', 12, 16)
    if (chunk === 'VP8 ') return [b.readUInt16LE(26) & 0x3fff, b.readUInt16LE(28) & 0x3fff]
    if (chunk === 'VP8L') {
      return [1 + (((b[22] & 0x3f) << 8) | b[21]),
              1 + (((b[24] & 0x0f) << 10) | (b[23] << 2) | ((b[22] & 0xc0) >> 6))]
    }
    if (chunk === 'VP8X') return [1 + b.readUIntLE(24, 3), 1 + b.readUIntLE(27, 3)]
  }
  return null
}

function scan(root) {
  const out = {}
  const add = (file, key) => {
    try {
      const size = readImageSize(fs.readFileSync(file))
      if (size) out[key] = size
    } catch { /* bỏ qua file không đọc được */ }
  }
  if (!fs.existsSync(root)) return out
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    if (entry.isFile() && IMAGE.test(entry.name)) add(path.join(root, entry.name), entry.name)
    if (entry.isDirectory()) {
      const sub = path.join(root, entry.name)
      for (const f of fs.readdirSync(sub)) {
        if (IMAGE.test(f)) add(path.join(sub, f), entry.name + '/' + f)
      }
    }
  }
  return out
}

export default function projectImageSizes({ dir = 'src/assets/projects' } = {}) {
  let root = ''
  return {
    name: 'project-image-sizes',
    configResolved(config) { root = path.resolve(config.root, dir) },
    resolveId(id) { return id === ID ? RESOLVED : null },
    load(id) {
      if (id !== RESOLVED) return null
      return 'export default ' + JSON.stringify(scan(root))
    },
    configureServer(server) {
      server.watcher.add(root)
      const onChange = file => {
        if (!path.resolve(file).startsWith(root) || !IMAGE.test(file)) return
        const mod = server.moduleGraph.getModuleById(RESOLVED)
        if (mod) server.moduleGraph.invalidateModule(mod)
        server.ws.send({ type: 'full-reload' })
      }
      for (const ev of ['add', 'unlink', 'change']) server.watcher.on(ev, onChange)
    }
  }
}
