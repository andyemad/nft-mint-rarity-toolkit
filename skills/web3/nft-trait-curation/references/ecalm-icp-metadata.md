# eCalm ICP metadata — session facts (2026-08-20/21)

Project: `~/Documents/Playground/ecalm-icp-metadata` (NOT the
mint-field-guide repo; no git commits there per Playground AGENTS.md).

- 200 tokens, contract `0x7deea22e46a01732eccbbd04fedb9860d8ea5b0e`, tiers:
  191 basic + 9 one_of_one (via `curation.tier`; token objects have no top-level
  tier field). Original attributes = only `Artist: peritrago`.
- Review server: `npm run review` → http://localhost:8733/basic-trait-review.html
  (also rarity-review.html). Trait draft: `data/analysis/basic-visual-traits.draft.json`,
  generator `scripts/build-basic-traits.mjs`, tests `test/basic-traits.test.mjs`
  (node --test, exact-array pins). Rebuild: `npm run traits:basic`.
- Categories as of revision g: Artwork (exclusive, all basic), Background /
  Skin Color / Lip Color (exclusive, finished=111), Motif (NON-exclusive,
  26 values, 95 of 111 assigned — 16 legitimately motif-free), Clothing
  (7 repeated outfits).
- User-confirmed decisions that MUST survive future audits: 118 NOT Cosmic Glow;
  glasses require real frames/lenses (127, 140, 154 rejected); smoke requires a
  visible cigarette; Woman variants identified by eyelashes; 164 is Skeleton and
  explicitly not horned; 173/196 are Basic Golden.
- Audit-wave assignments (2026-08-20f→g): 79→Cosmic Glow; 100→Glitch/Pixel;
  105→Bubbles; 122→Glasses+Headphones; 139→Floral Accessory+Companion+Hair/
  Headpiece (bow); 141 & 178→Woman (Eyelashes); 178 also Companion+Hair/Headpiece;
  112 white beret→Hair/Headpiece; 102→new value "Star Patches"; 147→Spiked Choker.
- Next step when Emad approves: merge draft into normalized catalog + canister
  structured traits. Until then drafts stay out of catalog/canister.
