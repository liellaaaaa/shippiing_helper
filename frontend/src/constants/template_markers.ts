// frontend/src/constants/template_markers.ts
export const TEMPLATE_MARKERS: Record<string, Array<{ marker: string; label: string; description: string }>> = {
  booking: [
    { marker: "{{MARK_SHIPPER}}", label: "发货人", description: "发货人公司名称" },
    { marker: "{{MARK_PORT}}", label: "卸货港", description: "目的港/卸货港" },
    { marker: "{{MARK_GOODS_TABLE}}", label: "货物明细表", description: "品名/规格/毛重/体积表格起始位" },
  ],
  msds: [
    { marker: "{{product_name}}", label: "产品名称", description: "MSDS 产品名称" },
    { marker: "{{physical_form}}", label: "物理形态", description: "物理形态" },
    { marker: "{{ion_type}}", label: "离子类型", description: "离子/分子类型" },
    { marker: "{{ph}}", label: "pH值", description: "pH 值" },
  ],
}

export const TEMPLATE_TYPE_LABELS: Record<string, string> = {
  booking: "订舱单 (Booking)",
  msds: "MSDS物质安全表",
}