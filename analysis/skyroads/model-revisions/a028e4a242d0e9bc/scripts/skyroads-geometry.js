/* Exact integer predicates for the analysis viewer; Python and original-x86
 * differential checks are recorded separately. No floating-point physics. */
function createGeometry(tables) {
  const u16 = n => n & 65535;
  const fold = lateral => { const v = u16(23 - u16(Math.floor(u16(lateral) / 128) - 49) % 46); return v > 32767 || v === 0 ? u16(1 - v) : v; };
  function structureHit(tile, index, height) {
    index = u16(index); height = u16(height);
    if (index >= 38) return 0;
    const y = Math.floor(u16(height + 0xde00) / 128), kind = tile & 0xf00;
    switch (kind) {
      case 0x100: return +(tables.lower[index] <= y && y < tables.upper[index]);
      case 0x200: return +(height < 0x3200);
      case 0x300: return +(height < 0x3200 && tables.lower[index] <= y);
      case 0x400: return +(height < 0x3c00);
      case 0x500: return +(height < 0x3c00 && tables.lower[index] <= y);
      default: return kind;
    }
  }
  function supportHeight(tile, force = 0) { const kind = (tile >> 8) & 15; return !kind || u16(force) ? (tile & 15 ? 0x2800 : 0) : kind === 1 ? 0 : tables.support[kind]; }
  function unsafeLanding(tile) { const kind = tile & 0xf00; if (kind === 0x100) return 0; const surface = (kind ? tile >> 4 : tile) & 15; return +((surface === 0 && kind === 0) || surface === 12); }
  function lookup(rows, forward, lateral) {
    const u = u16(Math.floor(u16(lateral) / 128) - 95);
    if (u >= 322) return 0;
    const row = Math.floor((forward >>> 0) / 65536), col = Math.floor(u / 46);
    if (row >= 500) throw new Error('Road allocation exceeded');
    return rows[row]?.[col] ?? 0;
  }
  function insideTunnel(rows, forward, lateral, height) {
    const tile = lookup(rows, forward, lateral), kind = tile & 0xf00, index = fold(lateral);
    if (![0x100, 0x300, 0x500].includes(kind) || index >= 38) return 0;
    return +(Math.floor(u16(u16(height) + 0xde00) / 128) < Math.floor(u16(tables.lower[index] + tables.upper[index]) / 2));
  }
  function positionHit(rows, forward, lateral, height) {
    lateral = u16(lateral); height = u16(height);
    const right = lookup(rows, forward, lateral + 0x700), left = lookup(rows, forward, lateral - 0x700);
    if (((right & 15) || (left & 15)) && height < 0x2800 && u16(height + 0x600) > 0x2480) return 1;
    if (u16(height + 0x680) <= 0x2800 || !((left | right) & 0xf00)) return 0;
    const raw = u16(23 - u16(Math.floor(lateral / 128) - 49) % 46), index = fold(lateral);
    if (structureHit(lookup(rows, forward, lateral), index, height)) return 1;
    return +!!structureHit(lookup(rows, forward, lateral + (raw > 32767 || raw === 0 ? 0x1700 : -0x1700)), u16(47 - index), height);
  }
  return { fold, structureHit, supportHeight, unsafeLanding, lookup, insideTunnel, positionHit };
}
if (typeof module !== 'undefined') module.exports = { createGeometry };
