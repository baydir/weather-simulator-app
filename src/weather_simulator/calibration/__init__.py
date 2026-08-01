"""Cloud-cover correction grid: coefficient table and interpolation.

Coefficients are precomputed offline and shipped as a server-side resource on a
fixed worldwide 0.5-degree grid anchored at exact multiples from -180 and -90.
At request time the four surrounding nodes are located, interpolated and
applied, with no external call. Outside the covered area the search is refused.
"""
