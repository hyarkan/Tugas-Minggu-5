# AI Usage Log

## Minggu 3

### Fitur
Fondasi aplikasi PMB: model tiga tabel, migration Alembic, endpoint registrasi, validasi input, dan penanganan email duplikat.

### Tujuan
Menggunakan AI sebagai alat bantu untuk memahami rancangan dan mempercepat implementasi aplikasi PMB.

### LLM atau tool
ChatGPT.

### Prompt kunci
"Bantu saya mengembangkan aplikasi PMB berbasis FastAPI menggunakan SQLAlchemy 2.0 dan Alembic. Implementasikan tiga model tabel beserta atribut dan constraint yang diperlukan, konfigurasi migrasi database dengan pengujian upgrade dan downgrade, serta buat endpoint POST /api/pmb/register. Pastikan endpoint memiliki validasi input dan menolak email duplikat dengan HTTP 409."

### Revisi manual
Memeriksa model, relasi, validasi, migration, endpoint, serta hasil pengujian secara manual.

### Hasil uji
Registrasi valid `201`, email duplikat `409`, tanggal lahir tidak valid `422`, dan referensi tidak ditemukan `400`.

## Minggu 4

### Fitur
Endpoint approve/reject, generator NIM, endpoint status dan statistik, pengujian Pytest, dokumentasi Swagger, dan README.

### Tujuan
Menyelesaikan alur PMB serta memastikan pembuatan NIM konsisten ketika approve diulang atau beberapa permintaan diproses berdekatan.

### LLM atau tool
ChatGPT sebagai alat bantu analisis, penyusunan kode, dokumentasi, dan debugging; Pytest dan pytest-cov untuk verifikasi otomatis.

### Prompt kunci
"Perluas aplikasi PMB FastAPI dan SQLAlchemy 2.0 yang sudah ada. Tambahkan endpoint PUT approve/reject, generator NIM dengan format 4 digit tahun + 3 digit kode prodi + 4 digit nomor urut, idempotensi, counter database, transaksi, penguncian sesuai dialect SQLite/MySQL, unique constraint, endpoint GET status dan statistik dengan GROUP BY, serta integration test Pytest. Generator tidak boleh melakukan commit sendiri. Sertakan pengujian approve berulang, data invalid, dan target coverage minimal 80%."

### Revisi manual
- Memilih format NIM 11 digit tanpa strip (`YYYYKKKNNNN`) dan mendokumentasikannya.
- Menggunakan tabel counter dengan primary key gabungan tahun dan kode prodi.
- Memastikan generator hanya melakukan flush dan transaksi/commit dimiliki fungsi approve.
- Menggunakan `BEGIN IMMEDIATE` pada SQLite karena SQLite tidak mendukung row-level `SELECT FOR UPDATE`.
- Menggunakan `SELECT FOR UPDATE` pada database yang mendukungnya serta mempertahankan unique constraint NIM.
- Mempertahankan respons validasi Pydantic/FastAPI `422` untuk nomor telepon tidak valid, sesuai pilihan desain yang sudah dicatat di README.
- Menambahkan kasus uji approve idempotent yang memastikan counter tidak bertambah saat approve diulang.

### OPAR

**Observe:** Modul PMB Minggu 3 belum memiliki alur approve/reject dan generator NIM. Approve berulang dapat menghasilkan nomor baru, sedangkan dua approve bersamaan berisiko membaca nomor urut yang sama.

**Plan:** Menambahkan tabel counter per tahun dan kode prodi, transaksi database, penguncian sesuai database, unique constraint, serta pengujian idempotensi dan kasus error.

**Act:** Mengimplementasikan endpoint approve/reject, generator NIM, endpoint status/stats, migration counter, dokumentasi, dan tes otomatis.

**Reflect:** Tes SQLite memverifikasi alur aplikasi dan idempotensi, tetapi tidak membuktikan row locking MySQL atau race condition multi-worker di lingkungan produksi. Pengujian beban dan verifikasi MySQL masih diperlukan jika lingkungan tersebut tersedia.

### Hasil uji
Perintah `pytest --cov=app --cov-report=term-missing --cov-fail-under=80` berhasil dijalankan. Hasil verifikasi: 15 tes lulus dan total coverage 81,38%, sehingga melewati target minimal 80%.

## Peran Mahasiswa

Mahasiswa bertanggung jawab meninjau kode yang dihasilkan atau disarankan AI, memahami alur transaksi dan penguncian, menjalankan pengujian, memeriksa hasil, serta memastikan dokumentasi sesuai implementasi.

## Pernyataan

AI digunakan sebagai alat bantu. Verifikasi, pemahaman, dan tanggung jawab atas hasil akhir tetap berada pada mahasiswa.


## Minggu 5 – Modul KRS

### Tujuan
Melanjutkan aplikasi PMB menjadi fondasi modul KRS dengan skema relasional, service pengelola KRS, empat validator, query prasyarat, dan perlindungan transaksi.

### Prompt kunci
"Lanjutkan project FastAPI dan SQLAlchemy 2.0 yang sudah ada tanpa merusak modul PMB. Tambahkan model dan migration untuk matakuliah, krs, krs_detail, prerequisite self-reference, serta skala_nilai. Implementasikan KRSManager add/remove/validate, Chain of Responsibility dengan empat validator, query prasyarat NOT EXISTS yang membandingkan bobot nilai minimal C, deteksi bentrok menggunakan irisan interval, constraint unik, dan transaksi dengan row lock. Tambahkan endpoint, seed dummy, dokumentasi keputusan desain, dan pengujian." 

### Revisi manual dan keputusan
- Menggunakan format semester `YYYY1` (ganjil) dan `YYYY2` (genap) agar urutan string sesuai urutan semester.
- Menambahkan `skala_nilai` agar nilai huruf tidak dibandingkan secara leksikografis; nilai C memiliki bobot 2 dan dinyatakan lulus.
- Menempatkan `DuplicateValidator` pertama karena murah dan tidak membutuhkan query; urutan serta alasan dicatat pada ADR-001.
- Memakai rumus irisan interval: hari sama, `mulai_A < selesai_B`, dan `mulai_B < selesai_A`.
- Menjalankan validasi dan insert dalam satu transaksi; memakai `SELECT FOR UPDATE` pada database yang mendukungnya dan `BEGIN IMMEDIATE` untuk SQLite.
- Minggu 5 hanya menyediakan status KRS serta operasi add/remove/validate. Transisi state machine submit/approve tetap menjadi pekerjaan Minggu 6.

### OPAR
**Observe:** Modul PMB sudah menghasilkan NIM, tetapi belum menyediakan relasi dan aturan pengambilan mata kuliah. Validasi tanpa penguncian dapat menyebabkan dua permintaan bersamaan melewati batas SKS.

**Plan:** Menambahkan lima tabel terkait KRS, rantai validator, query prasyarat berbasis NOT EXISTS, constraint, transaksi, endpoint, dan pengujian.

**Act:** Menambahkan model, migration 0003, seed mata kuliah dan skala nilai dummy, service, validator, endpoint KRS, ADR, dokumentasi, serta tes regresi PMB dan tes KRS.

**Reflect:** Pengujian SQLite dapat memverifikasi aturan aplikasi dan transaksi dasar, tetapi tidak membuktikan row-level locking MySQL. Hasil EXPLAIN aktual perlu diambil setelah migration dan seed pada database yang digunakan. State machine dan Hypothesis tetap dialokasikan untuk Minggu 6 sesuai video dosen.
