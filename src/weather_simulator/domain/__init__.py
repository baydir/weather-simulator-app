"""Rules settled in docs/regles.md: sky class, thresholds, bias correction.

This layer is meant to be stable. The sky class is derived here, by a single
function called for both the past and the future segments — duplicating that
logic would reopen the divergence at the seam the whole design exists to
prevent.
"""
