# ADR-004: Frame and time-scale naming convention

## Status
Accepted

## Context
Mixing TEME/PEF/ITRS/ECEF without suffixes is a common source of silent geometry bugs.

## Decision
Every position/velocity variable is suffixed: `_teme`, `_itrs`, `_ecef` (observer WGS84), `_enu`, `_sez`. API boundaries require timezone-aware UTC; conversion to UT1/TT Julian Date is explicit. Polar motion applied PEF→ITRS.

## Consequences
- Verbose names; far fewer frame bugs
- Clear mapping to Vallado / astropy validation suites
