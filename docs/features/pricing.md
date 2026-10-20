# Pricing

The tokens are priced from a dated price table kept in this repository, at the price that applied on the day each call was made.

**Status:** designed, not built yet.

**Requirements:** R14, R15, R16, R17

## Expected behaviour

- **Dated prices.** Every price has an effective date, and each call uses the latest price dated on or before its UTC day. A price change is a new row with a later date, so history is never rewritten. The statements of how modifiers combine are dated the same way, so a changed combination reprices nothing earlier.
- **Each token type at its own rate.** Input, output, cache-write and cache-read tokens are priced separately. Cache writes use the rate for their cache lifetime, and where the lifetime is unknown the report gives the range between the two.
- **Modifiers.** Higher rates for long prompts, the inference region's multiplier, rates for speed and service tier, and a per-request rate for server-side tool requests such as web searches, all as the price table states them.
- **Nothing is guessed.** A model, attribute or combination that the price table does not price is counted in tokens, left out of the cost and named in the report.
- **Never fetched.** Prices are read from the table at the tool's own commit. The tool fetches no prices from anywhere.

## See also

- `cost-pricing` in `openspec/`, and design decision 4 of `add-pr-cost-calculator`.
