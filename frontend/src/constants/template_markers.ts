// frontend/src/constants/template_markers.ts
export const TEMPLATE_MARKERS: Record<string, Array<{ marker: string; label: string; description: string }>> = {
  booking: [
    { marker: "{{MARK_SHIPPER}}", label: "发货人", description: "发货人公司名称" },
    { marker: "{{MARK_PORT}}", label: "卸货港", description: "目的港/卸货港" },
    { marker: "{{MARK_GOODS_TABLE}}", label: "货物明细表", description: "品名/规格/毛重/体积表格起始位" },
  ],
  loi: [
    { marker: "{{shipper}}", label: "发货人", description: "发货人公司名称" },
    { marker: "{{consignee}}", label: "收货人", description: "收货人名称" },
    { marker: "{{consignee_address}}", label: "收货人地址", description: "收货人完整地址" },
    { marker: "{{port_of_discharge}}", label: "卸货港", description: "目的港" },
    { marker: "{{product_name_cn}}", label: "品名中文", description: "产品中文名称" },
    { marker: "{{product_name_en}}", label: "品名英文", description: "产品英文名称" },
    { marker: "{{hs_code}}", label: "H.S.编码", description: "海关编码" },
    { marker: "{{gross_weight}}", label: "毛重", description: "总毛重(kg)" },
    { marker: "{{volume}}", label: "体积", description: "总体积(CBM)" },
    { marker: "{{date}}", label: "日期", description: "合同日期" },
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
  loi: "LOI保函 (LOI)",
  msds: "MSDS物质安全表",
}