-- Optional user-editable aliases for the safe REAPER plugin inventory scanner.
-- Add local product names or language-specific names here. Do not put license
-- keys, file paths, or private account data in this file.

return {
  {
    id = "user_defined_eq",
    display_name = "User Defined EQ Alias",
    capabilities = { "static_eq" },
    aliases = {
      "MSEQ",
      "mseq",
    },
    fallback = "ReaEQ",
  },
  {
    id = "user_defined_dynamic_eq",
    display_name = "User Defined Dynamic EQ Alias",
    capabilities = { "dynamic_eq", "resonance_suppressor" },
    aliases = {
      "MAutoDynamicEQ",
      "MDynamicEQ",
    },
    fallback = "TDR Nova or ReaXcomp",
  },
  {
    id = "user_defined_opto_compressor",
    display_name = "User Defined Opto Compressor Alias",
    capabilities = { "compressor" },
    aliases = {
      "Kolin",
      "Koliv",
      "Kiive",
      "opto",
    },
    fallback = "ReaComp",
  },
}
