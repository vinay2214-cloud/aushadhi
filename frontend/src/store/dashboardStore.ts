import { create } from "zustand";
import type { StockStatus } from "../types/health-center";
import type { InventoryUrgency } from "../types/inventory";

interface DashboardState {
  selectedDistrict: string | null;
  selectedCenterId: string | null;
  stockStatusFilter: StockStatus | null;
  urgencyFilter: InventoryUrgency | null;
  setSelectedDistrict: (district: string | null) => void;
  setSelectedCenterId: (id: string | null) => void;
  setStockStatusFilter: (status: StockStatus | null) => void;
  setUrgencyFilter: (urgency: InventoryUrgency | null) => void;
  resetFilters: () => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  selectedDistrict: null,
  selectedCenterId: null,
  stockStatusFilter: null,
  urgencyFilter: null,
  setSelectedDistrict: (selectedDistrict) => set({ selectedDistrict }),
  setSelectedCenterId: (selectedCenterId) => set({ selectedCenterId }),
  setStockStatusFilter: (stockStatusFilter) => set({ stockStatusFilter }),
  setUrgencyFilter: (urgencyFilter) => set({ urgencyFilter }),
  resetFilters: () =>
    set({
      selectedDistrict: null,
      selectedCenterId: null,
      stockStatusFilter: null,
      urgencyFilter: null,
    }),
}));
