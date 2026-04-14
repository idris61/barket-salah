### Barketsalah

barketsalah

### İş akışı özeti

1. **Nakliye Talebi (Shipping Request):** Müşteri ve sevkiyat bilgileri toplanır; gerekirse tehlikeli madde belgesi eklenir.
2. **Fırsat:** Talep formundan *Fırsat oluştur* ile Opportunity açılır; talep durumu *Fırsata dönüştürüldü* olur.
3. **Taşıyıcıdan satınalma teklifi:** Fırsattan nakliyeci tedarikçiler için ayrı ayrı taslak *Supplier Quotation*; kalemler Nakliye Talebi + Charge Type kurallarına göre; müşteri satış teklifi ayrı adım.
4. **Müşteri teklifi ve fatura:** Tedarikçi teklifinden satış teklifi (fiyatlar kopyalanır, gerekirse satış teklifinde düzenlenir); kabul + gönderimde taslak satış faturası ve (onaylı tedarikçi teklifinde) taslak satınalma faturası; ödemeler Payment Entry ile.

Ayrıntılı Türkçe özet: [docs/workflow_tr.md](docs/workflow_tr.md).

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch HEAD
bench install-app barketsalah
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/barketsalah
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
