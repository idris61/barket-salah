# Teknik Notlar (Özet)

Bu doküman, projede incelediğimiz kodların **amaçlarını**, **işleyişlerini** ve ilgili **DocType/alan bağımlılıklarını** kısa ve net şekilde toplar.

## Kapsam
- Kod incelemesi ilerledikçe her dosya için bir bölüm eklenir.
- Bu doküman **özet**tir; uzun açıklama yerine “neyi yapıyor / hangi alanlara dayanıyor / hangi kuralları uyguluyor” odaklıdır.

## İncelenen dosyalar
- `barketsalah/api/charge_selection.py`

---

## `barketsalah/api/charge_selection.py`

### Amaç
`Shipping Request` bağlamına göre, otomatik eklenecek **varsayılan** `Charge Type` kayıtlarının uygun olanlarını seçip **isim listesi** olarak döndürmek.

### Fonksiyon
`list_charge_type_names_for_shipping_request(shipping_request: str | None) -> list[str]`

- **Girdi**: `shipping_request` (Shipping Request adı) veya `None`
- **Çıktı**: `list[str]` → seçilen `Charge Type.name`

### Uygulanan iyileştirmeler (minimum/clean)
- SR okuması `exists + get_doc` yerine **tek sorgu** ile (`frappe.db.get_value(..., as_dict=True)`) yapıldı.
- `Charge Type` alanı için **meta kontrolü kaldırıldı**; şema sabit kabul edilerek sadeleştirildi.
- Mümkün olan eleme koşulları **DB filtrelerine taşındı** (gereksiz satır çekmemek için); Python tarafı `name` listesine indirildi.
- Fonksiyon **client’tan çağrılabilir** olması için `@frappe.whitelist()` ile işaretlendi.

### Dayandığı belgeler (DocType) ve alanlar

**Shipping Request**
- `transport_mode` (Select: Sea/Air/Road/Rail)
- `insurance_requested` (Check)
- `dangerous_goods` (Check)

**Charge Type**
- `is_default` (Check)
- `category` (Select: Ocean/Origin/Destination/Customs/Inland/Insurance/Other)
- `only_for_dangerous_goods` (Check)

### Seçim kuralları (özet)
Fonksiyon `Charge Type (is_default=1)` kayıtlarını alır ve aşağıdaki koşullarla eler:
- `category == "Insurance"` ise → SR `insurance_requested=1` değilse dışla
- `category == "Ocean"` ise → SR `transport_mode` dolu ve `"Sea"` değilse dışla (boşsa dahil kalır)
- `only_for_dangerous_goods == 1` ise → SR `dangerous_goods=1` değilse dışla

### İlgili iş kuralı (Shipping Request validate)
- SR’de `dangerous_goods=1` iken `dangerous_doc` boşsa doğrulamada hata verilir; kayıt engellenir.

