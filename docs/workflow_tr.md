# Barketsalah lojistik iş akışı (özet)

Bu belge, Barketsalah uygulamasının ERPNext üzerindeki hedef iş sürecini özetler. Ayrıntılı kurulum için kök dizindeki `README.md` dosyasına bakın.

## 1. Nakliye talebi (Shipping Request)

- Yeni belgeler **seri** alanı ile standart isim alır (ör. `SHIP-REQ-2026-00001`).
- Müşteriden gelen ilk talep **Nakliye Talebi** belgesinde toplanır: müşteri, rota, konteyner/taşıma bilgisi, sigorta talebi, tehlikeli madde ve adres alanları.
- **Durum** varsayılan olarak *Taslak* (*Draft*) başlar.
- Tehlikeli madde işaretlenmişse **Tehlikeli madde belgesi** yüklenmesi zorunludur (form ve sunucu doğrulaması).

## 2. Fırsat oluşturma

- Talep kaydından **Fırsat oluştur** (*Make Opportunity*) ile CRM tarafında **Fırsat** (*Opportunity*) açılır; talebe geri bağlantı `Shipping Request` alanı ile yazılır.
- Bu adımda talebin **Durumu** otomatik olarak *Fırsata dönüştürüldü* (*Converted to Opportunity*) olur.
- **Silme:** Fırsat veya nakliye talebi silindiğinde karşı taraftaki link alanı uygulama tarafından temizlenir; böylece çift yönlü bağlantıyı elle kaldırmadan silinebilir (Frappe `on_trash` sırası). Fırsat silindiğinde talebin **Durumu** tekrar *Taslak* (*Draft*) yapılır ve **Fırsat** linki boşalır; formu yenileyince **Fırsat oluştur** yeniden görünür.
- **Bağlantılar sekmesi:** Nakliye Talebi formunda, bu talebe bağlı **Fırsat**, **Tedarikçi Fiyat Teklifi** (*Supplier Quotation*) ve **Satış Siparişi** kayıtları DocType `links` tanımı ile listelenir (çekirdek belgelerdeki gibi).

## 3. Taşıyıcıdan satınalma fiyat teklifi (Supplier Quotation)

- İlgili fırsatta **Nakliyeci tedarikçi fiyat teklifleri oluştur** (*Create Carrier Supplier Quotations*) ile, **Nakliyeci** (*is_transporter*) işaretli her tedarikçi için ayrı bir taslak **Tedarikçi Fiyat Teklifi** (*Supplier Quotation*) oluşturulur.
- **Kalemler:** *Varsayılan* (*is_default*) işaretli **Charge Type** kayıtlarından seçilir; **Nakliye Talebi** alanlarına göre süzülür: kategori **Insurance** yalnızca sigorta talep edildiyse; kategori **Ocean** yalnızca taşıma modu *Deniz* (veya boş) ise; *Only for dangerous goods* işaretli ücret türleri yalnızca tehlikeli madde işaretliyse. **Item** yoksa otomatik oluşturulur.
- Belgeler **Fırsat** ve (varsa) **Nakliye Talebi** ile bağlanır; aynı fırsat + tedarikçi için açık bir tedarikçi teklifi zaten varken yinelenmez.

## 4. Müşteri satış teklifi (Quotation) ve kar

- **Tedarikçi Fiyat Teklifi** formunda **Müşteri teklifi oluştur** ile tedarikçi kalem satırları ve birim fiyatları aynen kopyalanarak müşteriye **Satış Teklifi** (*Quotation*) açılır; gerekirse fiyatlar satış teklifinde düzenlenir. Kaynak tedarikçi teklifi teklif üzerinde saklanır.
- Aynı tedarikçi teklifi için yalnızca bir açık müşteri teklifi oluşturulabilir.
- **Teklif durumu (*Quote Status*):** *Accepted* yapıldığında (kaydetme): aynı fırsattaki diğer müşteri teklifleri *Rejected* olur; aynı fırsattaki diğer **Tedarikçi Fiyat Teklifleri**nin *Müşteri kararı* alanı *Lost*, kazanan kaynak teklif *Won* olur. *Rejected* yapıldığında, bu teklifin kaynak tedarikçi teklifine bağlı *Müşteri kararı* *Lost* yapılır (kaynak teklif tanımlıysa).

## 5. Faturalar ve ödeme

- Müşteri teklifi **Gönderildi** (*Submit*) edilirken *Quote Status* = *Accepted* ise: taslak **Satış Siparişi** (*Sales Order*), taslak **Satış Faturası** (*Sales Invoice*) ve (kaynak tedarikçi teklifi **onaylı** ise) taslak **Satınalma Faturası** (*Purchase Invoice*) otomatik oluşturulur; teklif ve tedarikçi teklifi üzerinde ilgili link alanları dolar. Tedarikçi teklifi henüz onaylı değilse satınalma faturası atlanır ve uyarı gösterilir.
- **Ödeme:** ERPNext **Ödeme Girişi** (*Payment Entry*) ile satış ve satınalma faturalarına standart tahsilat / ödeme kaydı.
- **Sevkiyat:** İhtiyaç halinde satış siparişi / sevkiyat adımları ERPNext standart akışıyla devam edebilir (uygulama şu aşamada doğrudan faturayı önceliklendirir).

## Çeviriler

- **Nakliye Talebi** form etiketleri ve ilgili sabit metinlerin Türkçe karşılıkları `barketsalah/translations/tr.csv` dosyasındadır. Kullanıcı dilini Türkçe yaptıktan sonra gerekirse `bench build` ve önbellek yenilemesi uygulanır.
