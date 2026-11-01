import { describe, expect, it } from 'vitest'
import { galleryRows } from './galleryRows'
import { readImageSize } from '../../vite-plugins/projectImageSizes.js'

const img = (name, w, h) => ({ src: name, w, h })
const shape = rows => rows.map(r => r.items.map(i => i.src).join('+') + (r.lone ? '(lone)' : ''))

describe('galleryRows', () => {
  it('groups the project-01 sequence like the spec', () => {
    const L = (n) => img(n, 2048, 1463), S = (n) => img(n, 2048, 2048), P = (n) => img(n, 2048, 2562)
    const rows = galleryRows([L('1'), L('2'), S('3'), P('4'), P('5'), S('6'), S('7'), L('8'), L('9')])
    expect(shape(rows)).toEqual(['1', '2', '3+4', '5+6', '7(lone)', '8', '9'])
  })

  it('keeps every landscape photo on its own row', () => {
    expect(shape(galleryRows([img('a', 1600, 900), img('b', 1500, 1000)]))).toEqual(['a', 'b'])
  })

  it('a landscape photo ends a pending pair', () => {
    expect(shape(galleryRows([img('p', 800, 1000), img('l', 1600, 900), img('q', 800, 1000)])))
      .toEqual(['p(lone)', 'l', 'q(lone)'])
  })

  it('pairs an even run and leaves the last of an odd run alone', () => {
    const P = n => img(n, 800, 1000)
    expect(shape(galleryRows([P('1'), P('2'), P('3')]))).toEqual(['1+2', '3(lone)'])
  })

  it('returns no rows for no photos', () => {
    expect(galleryRows([])).toEqual([])
  })
})

describe('readImageSize', () => {
  it('reads PNG', () => {
    const b = Buffer.alloc(32)
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]).copy(b, 0)
    b.writeUInt32BE(1200, 16); b.writeUInt32BE(800, 20)
    expect(readImageSize(b)).toEqual([1200, 800])
  })

  it('reads JPEG past an APP0 segment', () => {
    const app0 = [0xff, 0xe0, 0x00, 0x10, ...new Array(14).fill(0)]
    const sof0 = [0xff, 0xc0, 0x00, 0x11, 0x08, 0x05, 0x00, 0x08, 0x00, 0x03, ...new Array(9).fill(0)]
    const b = Buffer.from([0xff, 0xd8, ...app0, ...sof0, 0xff, 0xd9])
    expect(readImageSize(b)).toEqual([2048, 1280])
  })

  it('returns null for unknown data', () => {
    expect(readImageSize(Buffer.alloc(40))).toBeNull()
  })
})
