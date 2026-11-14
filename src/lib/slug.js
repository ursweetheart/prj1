/* The server's code rule for a new taxonomy dimension or value (backend pipeline/taxonomy_admin.slug):
 * lower case, no accents, every run of other characters becomes one '_'. Used for the preview only. */
export function slug(name) {
  return (name || '').toLowerCase().replace(/đ/g, 'd').normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 60)
}
