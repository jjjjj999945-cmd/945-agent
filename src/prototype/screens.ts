export type StitchScreen = {
  index: number;
  title: string;
  shortTitle: string;
  navLabel: string;
  route: string;
  folder: string;
  primary: boolean;
  assets: { url: string; file: string }[];
};

export const screens: StitchScreen[] = [
  {
    index: 1,
    title: "945 - Today Dashboard (Refined Glacier Light)",
    shortTitle: "Today Dashboard",
    navLabel: "Today",
    route: "",
    folder: "01-945-today-dashboard-refined-glacier-light-d8d7d3d7",
    primary: true,
    assets: [
      { url: "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap", file: "assets/asset-001.bin" },
      { url: "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&family=Manrope:wght@400;500;600;700;800&display=swap", file: "assets/asset-002.bin" },
      { url: "https://cdn.tailwindcss.com?plugins=forms,container-queries", file: "assets/asset-003.bin" },
      { url: "https://lh3.googleusercontent.com/aida-public/AB6AXuAZZ8clIcHsc9cMqo0FWDFWeJkXiSRIrNLyf4iD84cjOkqGuNwLo4osK2VaPwhu4yJMqFMOKpj9oMZGANDByp7Ns7SdnJrDxtEheQi_-rsYWNBtx0ltS53e0cTPx5j6gUimdIKhyXh3uv_z07mofWPVtsP0uldNt0nciFYfUjvTPi-xJOHX2_vRuCPYn3O_tIMPrCyWQYWxfCBG51f1N5EQjz25EWTxq8La2aQppsJEafyVix1qpXEJ", file: "assets/asset-004.bin" },
      { url: "https://lh3.googleusercontent.com/aida-public/AB6AXuBfKxaNgMeDXoBJDlF-RHZiXyZUAmP-3oyuRK3hVXwL5mCDwePpqvXMMSwlC2GY3lC3q_NLTt69Qnh5jM72vS2pi6vbuBoKV_IzRFby0fXuQtcaXbRdHoSpmO5CM0nKbWqfDjkMtrzbjJizeGTmbssb9fS372VQrEWlQq01jftjUZrW5mSHg1EH6Hyj8V2QbO_RTnqLkHmexwIvLHrqtceRxZL9vSpeitLM-2u8IS2_13aYGdK2HWLW", file: "assets/asset-005.bin" },
    ]
  },
  {
    index: 2,
    title: "945 - Workout Detail (Refined Glacier Light) v3",
    shortTitle: "Workout Detail v3",
    navLabel: "Workout",
    route: "workout",
    folder: "02-945-workout-detail-refined-glacier-light-v3-d558e695",
    primary: true,
    assets: [
      { url: "https://cdn.tailwindcss.com?plugins=forms,container-queries", file: "assets/asset-001.bin" },
      { url: "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap", file: "assets/asset-002.bin" },
      { url: "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Manrope:wght@400;500;600;700;800&display=swap", file: "assets/asset-003.bin" },
      { url: "https://lh3.googleusercontent.com/aida-public/AB6AXuBfKxaNgMeDXoBJDlF-RHZiXyZUAmP-3oyuRK3hVXwL5mCDwePpqvXMMSwlC2GY3lC3q_NLTt69Qnh5jM72vS2pi6vbuBoKV_IzRFby0fXuQtcaXbRdHoSpmO5CM0nKbWqfDjkMtrzbjJizeGTmbssb9fS372VQrEWlQq01jftjUZrW5mSHg1EH6Hyj8V2QbO_RTnqLkHmexwIvLHrqtceRxZL9vSpeitLM-2u8IS2_13aYGdK2HWLW", file: "assets/asset-004.bin" },
      { url: "https://lh3.googleusercontent.com/aida-public/AB6AXuAZZ8clIcHsc9cMqo0FWDFWeJkXiSRIrNLyf4iD84cjOkqGuNwLo4osK2VaPwhu4yJMqFMOKpj9oMZGANDByp7Ns7SdnJrDxtEheQi_-rsYWNBtx0ltS53e0cTPx5j6gUimdIKhyXh3uv_z07mofWPVtsP0uldNt0nciFYfUjvTPi-xJOHX2_vRuCPYn3O_tIMPrCyWQYWxfCBG51f1N5EQjz25EWTxq8La2aQppsJEafyVix1qpXEJ", file: "assets/asset-005.bin" },
    ]
  },
  {
    index: 3,
    title: "945 - Settings & Preferences (Refined Glacier Light) v2",
    shortTitle: "Settings & Preferences",
    navLabel: "Settings",
    route: "settings",
    folder: "03-945-settings-preferences-refined-glacier-light-v2-055ec8f8",
    primary: true,
    assets: [
      { url: "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap", file: "assets/asset-001.bin" },
      { url: "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=block", file: "assets/asset-002.bin" },
      { url: "https://cdn.tailwindcss.com?plugins=forms,container-queries", file: "assets/asset-003.bin" },
      { url: "https://lh3.googleusercontent.com/aida-public/AB6AXuAZZ8clIcHsc9cMqo0FWDFWeJkXiSRIrNLyf4iD84cjOkqGuNwLo4osK2VaPwhu4yJMqFMOKpj9oMZGANDByp7Ns7SdnJrDxtEheQi_-rsYWNBtx0ltS53e0cTPx5j6gUimdIKhyXh3uv_z07mofWPVtsP0uldNt0nciFYfUjvTPi-xJOHX2_vRuCPYn3O_tIMPrCyWQYWxfCBG51f1N5EQjz25EWTxq8La2aQppsJEafyVix1qpXEJ", file: "assets/asset-004.bin" },
      { url: "https://lh3.googleusercontent.com/aida-public/AB6AXuBfKxaNgMeDXoBJDlF-RHZiXyZUAmP-3oyuRK3hVXwL5mCDwePpqvXMMSwlC2GY3lC3q_NLTt69Qnh5jM72vS2pi6vbuBoKV_IzRFby0fXuQtcaXbRdHoSpmO5CM0nKbWqfDjkMtrzbjJizeGTmbssb9fS372VQrEWlQq01jftjUZrW5mSHg1EH6Hyj8V2QbO_RTnqLkHmexwIvLHrqtceRxZL9vSpeitLM-2u8IS2_13aYGdK2HWLW", file: "assets/asset-005.bin" },
      { url: "https://lh3.googleusercontent.com/aida-public/AB6AXuDLOPIieJtXCz3sgW5oJz75E2pgTJBYIl_DTQQkzCLjC5grVoJoymfOBbusMsiVg029O99O0LBECTAuWFSq4hPVz-kDXn8Yk4fesazzIRaXjWsLUfVQ3DuM_FbhbghTNYLpiNhLPMDxU-B8fTqaW246E-oFjI54v5x-KdSbe_AhY_qjaQjTuoT29O63ca4RJIoHQrIoUZDMTF2G0Fo4incdFNUy730fwMKmImRtDbx7AFOOOx1EXjAg", file: "assets/asset-006.bin" },
    ]
  },
  {
    index: 4,
    title: "945 - Weekly Summary (Refined Glacier Light) v2",
    shortTitle: "Weekly Summary",
    navLabel: "Summary",
    route: "weekly-summary",
    folder: "04-945-weekly-summary-refined-glacier-light-v2-989cb938",
    primary: true,
    assets: [
      { url: "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=block", file: "assets/asset-001.bin" },
      { url: "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap", file: "assets/asset-002.bin" },
      { url: "https://cdn.tailwindcss.com?plugins=forms,container-queries", file: "assets/asset-003.bin" },
      { url: "https://lh3.googleusercontent.com/aida-public/AB6AXuAZZ8clIcHsc9cMqo0FWDFWeJkXiSRIrNLyf4iD84cjOkqGuNwLo4osK2VaPwhu4yJMqFMOKpj9oMZGANDByp7Ns7SdnJrDxtEheQi_-rsYWNBtx0ltS53e0cTPx5j6gUimdIKhyXh3uv_z07mofWPVtsP0uldNt0nciFYfUjvTPi-xJOHX2_vRuCPYn3O_tIMPrCyWQYWxfCBG51f1N5EQjz25EWTxq8La2aQppsJEafyVix1qpXEJ", file: "assets/asset-004.bin" },
      { url: "https://lh3.googleusercontent.com/aida-public/AB6AXuBfKxaNgMeDXoBJDlF-RHZiXyZUAmP-3oyuRK3hVXwL5mCDwePpqvXMMSwlC2GY3lC3q_NLTt69Qnh5jM72vS2pi6vbuBoKV_IzRFby0fXuQtcaXbRdHoSpmO5CM0nKbWqfDjkMtrzbjJizeGTmbssb9fS372VQrEWlQq01jftjUZrW5mSHg1EH6Hyj8V2QbO_RTnqLkHmexwIvLHrqtceRxZL9vSpeitLM-2u8IS2_13aYGdK2HWLW", file: "assets/asset-005.bin" },
    ]
  },
  {
    index: 5,
    title: "945 - Agent Chat (Refined Glacier Light) v3",
    shortTitle: "Agent Chat v3",
    navLabel: "Agent v3",
    route: "agent-v3",
    folder: "05-945-agent-chat-refined-glacier-light-v3-72fba579",
    primary: false,
    assets: [
      { url: "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap", file: "assets/asset-001.bin" },
      { url: "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&family=Manrope:wght@400;500;600;700;800&display=swap", file: "assets/asset-002.bin" },
      { url: "https://cdn.tailwindcss.com?plugins=forms,container-queries", file: "assets/asset-003.bin" },
      { url: "https://lh3.googleusercontent.com/aida-public/AB6AXuBnJswreeCQI1SBG9bG87xvaacF8bTTEy2JPNPKT_r6f7SIQRsFIkSJPfNEUBPE2urDcg25xOdCHJe-CxG7kr0rEWWzO4EpOdoyqeena5q-CVZxBzZziXfJyOLsvJJk6k1FePuAfC564SL_oEwZobONNFQtvtB-N0BRH4U-fECu4UGk7g8_H0n9RPACwz8njiOCw0Bfw_JTuHvVGBXyNsmyNimoqs8a1oVk6Be4rJneik-snZtTrJ_R", file: "assets/asset-004.bin" },
      { url: "https://lh3.googleusercontent.com/aida-public/AB6AXuChtprByaM-ICnE08uQynseJvxJ_lUrP3cpyRBJrUoAHsSWN8BXo0MFKsiApjAFnjLcaxUglHwHv9OtrwUSBj3i1ux8Q8vBVmDb4vWSzay6P5ViuOi-BCtOBLuwlmneQpVfEj7YCBltx7OH8twfz0pK89qlTYUq2AACCer0vYCPeFqgWix5AJz_TF3Aff6mf8O8dEOPIsQH0AIzLlI4fo7yuwUKtBRF6QWO8mm1Sv337bqDkHuyjoHB", file: "assets/asset-005.bin" },
    ]
  },
  {
    index: 6,
    title: "945 - Diet Tracker (Refined Glacier Light) v2",
    shortTitle: "Diet Tracker v2",
    navLabel: "Diet",
    route: "diet",
    folder: "06-945-diet-tracker-refined-glacier-light-v2-6685d645",
    primary: true,
    assets: [
      { url: "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap", file: "assets/asset-001.bin" },
      { url: "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&family=Manrope:wght@400;500;600;700;800&display=swap", file: "assets/asset-002.bin" },
      { url: "https://cdn.tailwindcss.com?plugins=forms,container-queries", file: "assets/asset-003.bin" },
      { url: "https://lh3.googleusercontent.com/aida-public/AB6AXuAZZ8clIcHsc9cMqo0FWDFWeJkXiSRIrNLyf4iD84cjOkqGuNwLo4osK2VaPwhu4yJMqFMOKpj9oMZGANDByp7Ns7SdnJrDxtEheQi_-rsYWNBtx0ltS53e0cTPx5j6gUimdIKhyXh3uv_z07mofWPVtsP0uldNt0nciFYfUjvTPi-xJOHX2_vRuCPYn3O_tIMPrCyWQYWxfCBG51f1N5EQjz25EWTxq8La2aQppsJEafyVix1qpXEJ", file: "assets/asset-004.bin" },
      { url: "https://lh3.googleusercontent.com/aida-public/AB6AXuBfKxaNgMeDXoBJDlF-RHZiXyZUAmP-3oyuRK3hVXwL5mCDwePpqvXMMSwlC2GY3lC3q_NLTt69Qnh5jM72vS2pi6vbuBoKV_IzRFby0fXuQtcaXbRdHoSpmO5CM0nKbWqfDjkMtrzbjJizeGTmbssb9fS372VQrEWlQq01jftjUZrW5mSHg1EH6Hyj8V2QbO_RTnqLkHmexwIvLHrqtceRxZL9vSpeitLM-2u8IS2_13aYGdK2HWLW", file: "assets/asset-005.bin" },
      { url: "https://lh3.googleusercontent.com/aida-public/AB6AXuAof4sXQA8P0udN6ijYjM1_7ZRR322jF8z5m3PRExTIZfV2J_adAzHePMkL2JMylaPsXCBB1xpxhIjIV6gzdQdygZpUKH5fahxPO6DgeejOiqpt-kqQB2eb0ulKxKNiviIOHJmwTBF3Kzwk_sAy4jbwTHLPG-yHmUuD7YEC6d-OhZNz_SQFGe-B7sk1t8IfvxEzNdjY-gUxtC1K1iaTj5UG7EW-q0oXuhpLAdjZaCkqDl8-10_HLcfA", file: "assets/asset-006.bin" },
      { url: "https://lh3.googleusercontent.com/aida-public/AB6AXuD3aL1ba7jOcggmFWs5XLAyKXKYiGKk6dtiXXrHW6oskj9KV-tV-3GOkrrOVzzWL1QT5mTLhqeN5vDlXPVx3yzJ55Kw_zIB3HF49d6BK2JTQucrDYpu7HJDh0GJREaqZ_dmRKxaGzf0lhkLZLSsv9XhTx64i8rGRXuckb48Lz5TnDEfW9PdHOwb9YE8jPsZnfbHDx0i4JS_pP4CxjCPuII8kdogsxkOp89IeYc_rQ9capjs9VdPKmUC", file: "assets/asset-007.bin" },
    ]
  },
  {
    index: 7,
    title: "945 - Workout Detail (Refined Glacier Light)",
    shortTitle: "Workout Detail",
    navLabel: "Workout alt",
    route: "workout-alt",
    folder: "07-945-workout-detail-refined-glacier-light-f59fdfcf",
    primary: false,
    assets: [
      { url: "https://cdn.tailwindcss.com?plugins=forms,container-queries", file: "assets/asset-001.bin" },
      { url: "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap", file: "assets/asset-002.bin" },
      { url: "https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap", file: "assets/asset-003.bin" },
    ]
  },
  {
    index: 8,
    title: "945 - Agent Chat (Refined Glacier Light) Final Calibration",
    shortTitle: "Agent Chat Final",
    navLabel: "Agent",
    route: "agent",
    folder: "08-945-agent-chat-refined-glacier-light-final-calibration-61a5ca3f",
    primary: true,
    assets: [
      { url: "https://cdn.tailwindcss.com?plugins=forms,container-queries", file: "assets/asset-001.bin" },
      { url: "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap", file: "assets/asset-002.bin" },
      { url: "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap", file: "assets/asset-003.bin" },
      { url: "https://lh3.googleusercontent.com/aida-public/AB6AXuBnJswreeCQI1SBG9bG87xvaacF8bTTEy2JPNPKT_r6f7SIQRsFIkSJPfNEUBPE2urDcg25xOdCHJe-CxG7kr0rEWWzO4EpOdoyqeena5q-CVZxBzZziXfJyOLsvJJk6k1FePuAfC564SL_oEwZobONNFQtvtB-N0BRH4U-fECu4UGk7g8_H0n9RPACwz8njiOCw0Bfw_JTuHvVGBXyNsmyNimoqs8a1oVk6Be4rJneik-snZtTrJ_R", file: "assets/asset-004.bin" },
      { url: "https://lh3.googleusercontent.com/aida-public/AB6AXuChtprByaM-ICnE08uQynseJvxJ_lUrP3cpyRBJrUoAHsSWN8BXo0MFKsiApjAFnjLcaxUglHwHv9OtrwUSBj3i1ux8Q8vBVmDb4vWSzay6P5ViuOi-BCtOBLuwlmneQpVfEj7YCBltx7OH8twfz0pK89qlTYUq2AACCer0vYCPeFqgWix5AJz_TF3Aff6mf8O8dEOPIsQH0AIzLlI4fo7yuwUKtBRF6QWO8mm1Sv337bqDkHuyjoHB", file: "assets/asset-005.bin" },
    ]
  },
  {
    index: 9,
    title: "945 - Onboarding (Refined Glacier Light)",
    shortTitle: "Onboarding",
    navLabel: "Onboarding",
    route: "onboarding",
    folder: "09-945-onboarding-refined-glacier-light-1ba4e092",
    primary: true,
    assets: [
      { url: "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=block", file: "assets/asset-001.bin" },
      { url: "https://cdn.tailwindcss.com?plugins=forms,container-queries", file: "assets/asset-002.bin" },
    ]
  },
  {
    index: 10,
    title: "945 - AI Adjustment Analysis",
    shortTitle: "AI Adjustment",
    navLabel: "AI Analysis",
    route: "ai-adjustment",
    folder: "10-945-ai-adjustment-analysis-cdef0de7",
    primary: true,
    assets: [
      { url: "https://cdn.tailwindcss.com?plugins=forms,container-queries", file: "assets/asset-001.bin" },
      { url: "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap", file: "assets/asset-002.bin" },
      { url: "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap", file: "assets/asset-003.bin" },
      { url: "https://lh3.googleusercontent.com/aida-public/AB6AXuAdQ-KXh4lb9cGXnUbxoO13FfQkjEfgMOEJd_veWXxfMSAf1Go90vuQDFGL1uv0Kp1DEyYgWWCblwPOMNCEglO7lyIXM0Wcc5jT-oH-Tre8GFsZyn8qm9Z89Tcz43KmQ1k-pChwtF9BMDBRNWp80luUng6XYiVXQPvSwkzeoJa3OM_2vP9cKafHFddwxjC4E8xNHs20gXOccTcF7Wz90kFzEaICoD9NUBhP04Qx9wlL5gkW22tajSOO", file: "assets/asset-004.bin" },
      { url: "https://lh3.googleusercontent.com/aida-public/AB6AXuDbJiau59uJSqIfkUfNUJgE27sHKvQaUmpI2CKoovu66LPY27cpyPfDDtxgJmuIP9ykzI8EvOUcxeaTPXI-6tcGel8kSkU1Lu30J4L9LkToDo36bXIV5wKdVYB2GO_dEfrqcq5mehiucaVNf-wYIc0W-z2lOoHam6Dd4lKEoyrVUOJiLTd0fwe463b-Lg9O6NoLI8pGwoZsVE-zAXw9lC_IEBa3Jpi_mFCiZ_cnrXlv_-7bIwT5TzsM", file: "assets/asset-005.bin" },
    ]
  },
  {
    index: 11,
    title: "945 - Diet Tracker (Refined Glacier Light)",
    shortTitle: "Diet Tracker",
    navLabel: "Diet alt",
    route: "diet-alt",
    folder: "11-945-diet-tracker-refined-glacier-light-c1f8ff14",
    primary: false,
    assets: [
      { url: "https://cdn.tailwindcss.com?plugins=forms,container-queries", file: "assets/asset-001.bin" },
      { url: "https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap", file: "assets/asset-002.bin" },
      { url: "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap", file: "assets/asset-003.bin" },
      { url: "https://lh3.googleusercontent.com/aida-public/AB6AXuC-9sFVM1A-cJchZxRI1GppkUHLMn9Fww20JoaCQ7ouOocsTrrDfyBucIpbFgJiZ50jYH61OxvlMXlZl2kftFXb7dffccTuhQbtj7k0z1uQcvZuqEb7CxRl8GSa1d2vCm0DnUSPTolDWlhHoymkE3XYAtSqVCMPQaRBcVb4RbEd-MgckZ_5_tkpg-BMMMZbIF8vx0x0pTIEZv30XA2mBJGJEW6JFc5CyuHmGRJcHG1WFrcpQaAahhqV", file: "assets/asset-004.bin" },
      { url: "https://lh3.googleusercontent.com/aida-public/AB6AXuAof4sXQA8P0udN6ijYjM1_7ZRR322jF8z5m3PRExTIZfV2J_adAzHePMkL2JMylaPsXCBB1xpxhIjIV6gzdQdygZpUKH5fahxPO6DgeejOiqpt-kqQB2eb0ulKxKNiviIOHJmwTBF3Kzwk_sAy4jbwTHLPG-yHmUuD7YEC6d-OhZNz_SQFGe-B7sk1t8IfvxEzNdjY-gUxtC1K1iaTj5UG7EW-q0oXuhpLAdjZaCkqDl8-10_HLcfA", file: "assets/asset-005.bin" },
      { url: "https://lh3.googleusercontent.com/aida-public/AB6AXuD3aL1ba7jOcggmFWs5XLAyKXKYiGKk6dtiXXrHW6oskj9KV-tV-3GOkrrOVzzWL1QT5mTLhqeN5vDlXPVx3yzJ55Kw_zIB3HF49d6BK2JTQucrDYpu7HJDh0GJREaqZ_dmRKxaGzf0lhkLZLSsv9XhTx64i8rGRXuckb48Lz5TnDEfW9PdHOwb9YE8jPsZnfbHDx0i4JS_pP4CxjCPuII8kdogsxkOp89IeYc_rQ9capjs9VdPKmUC", file: "assets/asset-006.bin" },
    ]
  }
];
