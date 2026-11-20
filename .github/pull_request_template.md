## Fitur
- [ ] Endpoint approve/reject
- [ ] Generator NIM dan counter
- [ ] Endpoint status dan statistik
- [ ] Pengujian Pytest dan coverage
- [ ] Dokumentasi Swagger/README

## Isu yang diselesaikan
Jelaskan kebutuhan atau masalah yang ditangani oleh perubahan ini.

## Bantuan AI
Jelaskan bagian yang dibantu AI dan bagian yang diperiksa atau direvisi secara manual.

## Tiga prompt terbaik
1. Jelaskan prompt pertama yang digunakan.
2. Jelaskan prompt kedua yang digunakan.
3. Jelaskan prompt ketiga yang digunakan.

## Risiko dan limitasi
- SQLite tidak menyediakan row-level `SELECT FOR UPDATE`; implementasi menggunakan `BEGIN IMMEDIATE`.
- Tes SQLite in-memory tidak membuktikan perilaku locking MySQL atau race condition lintas worker.
- Uji beban dan validasi MySQL perlu dilakukan jika lingkungan tersebut tersedia.

## Cara pengujian
```bash
pytest --cov=app --cov-report=term-missing --cov-fail-under=80
```

## Bukti pengujian
Lampirkan screenshot atau log hasil migration, endpoint Swagger, skenario tes, dan laporan coverage.
