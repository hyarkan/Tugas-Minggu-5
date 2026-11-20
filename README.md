# Aplikasi PMB dan KRS — Tugas Minggu 3, 4, dan 5

Aplikasi Penerimaan Mahasiswa Baru berbasis FastAPI, SQLAlchemy 2.0, Alembic, dan SQLite.

## Fitur

- Registrasi calon mahasiswa dengan validasi Pydantic dan email unik.
- Persetujuan (`approve`) dan penolakan (`reject`) pendaftar.
- Generator NIM otomatis dengan format `YYYYKKKNNNN` (11 digit, tanpa strip).
- Counter NIM terpisah berdasarkan kombinasi tahun dan kode program studi.
- Approve idempotent: approve berulang mengembalikan NIM lama tanpa menaikkan counter.
- Proteksi transaksi dan penguncian database untuk menghindari nomor urut ganda.
- Endpoint status pendaftaran dan statistik menggunakan agregasi `GROUP BY`.
- Pengujian otomatis Pytest dan laporan coverage.
- Modul KRS: empat tabel inti (`matakuliah`, `krs`, `krs_detail`, `prerequisite`) ditambah `skala_nilai`.
- KRS Manager untuk menambah, menghapus, dan memvalidasi mata kuliah.
- Chain of Responsibility dengan empat validator: duplikasi, SKS, prasyarat, dan bentrok jadwal.
- Query prasyarat menggunakan `NOT EXISTS` dan pembobotan nilai numerik.
- Penguncian KRS dan transaksi untuk mencegah race condition saat penambahan mata kuliah.

## Format NIM

NIM disimpan sebagai 11 digit angka: `YYYYKKKNNNN`.

- `YYYY`: tahun persetujuan (UTC).
- `KKK`: kode program studi, tepat tiga digit angka.
- `NNNN`: nomor urut empat digit, dimulai dari `0001` untuk setiap kombinasi tahun dan kode prodi.

Contoh: `20260010001`. Format tanpa strip dipilih agar konsisten dengan pola 11 digit yang diminta pada contoh pengujian video. Keputusan ini didokumentasikan di README.

## Menjalankan aplikasi

```bash
python -m venv .venv
```

Windows:
```powershell
.venv\Scripts\Activate.ps1
```

Install dependensi dan buat database:
```bash
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

Buka Swagger UI: http://127.0.0.1:8000/docs  
Alternatif dokumentasi: http://127.0.0.1:8000/redoc

## Data referensi

Kode program studi untuk generator NIM wajib berupa tiga digit angka, misalnya `001` atau `002`. Seed awal menyiapkan kode `001` untuk Sistem Informasi dan kode jalur masuk SNBP, SNBT, serta Mandiri. Jika database lama masih memiliki kode nonnumerik seperti `SIF`, ubah kode tersebut menjadi kode tiga digit sebelum melakukan approve.

```bash
python -m app.seed
```

## Endpoint API

| Method | Endpoint | Fungsi |
|---|---|---|
| POST | `/api/pmb/register` | Registrasi calon mahasiswa |
| PUT | `/api/pmb/{candidate_id}/approve` | Menyetujui pendaftar dan membuat NIM |
| PUT | `/api/pmb/{candidate_id}/reject` | Menolak pendaftar pending |
| GET | `/api/pmb/status/{candidate_id}` | Melihat status pendaftaran |
| GET | `/api/pmb/stats` | Statistik pendaftar |

### Kode respons penting

- `201`: registrasi berhasil.
- `200`: approve/reject/status/stats berhasil.
- `400`: referensi atau kode program studi untuk NIM tidak valid.
- `404`: ID pendaftar tidak ditemukan.
- `409`: email duplikat atau konflik transisi status.
- `422`: format request gagal divalidasi Pydantic/FastAPI (termasuk nomor telepon tidak valid).

## Strategi konsistensi NIM

- Kolom `calon_mahasiswa.nim` memiliki unique constraint sebagai perlindungan terakhir.
- Counter memiliki primary key gabungan `tahun` dan `kode_prodi`.
- Generator menaikkan counter dalam transaksi endpoint approve dan tidak melakukan commit sendiri.
- Pada MySQL/InnoDB, query counter menggunakan `SELECT ... FOR UPDATE`; unique constraint dan retry menjadi perlindungan untuk konflik pembuatan counter pertama.
- SQLite tidak mendukung row-level `SELECT FOR UPDATE`. Karena itu, proses approve memulai transaksi dengan `BEGIN IMMEDIATE` sebelum membaca data sehingga transaksi penulis terserialisasi. Unique constraint NIM tetap aktif.
- SQLite in-memory pada pengujian tidak membuktikan perilaku row lock MySQL. Uji beban multi-worker dan verifikasi locking MySQL masih perlu dilakukan bila lingkungan MySQL tersedia.

## Pengujian

Jalankan semua tes dan ukur coverage:

```bash
pytest --cov=app --cov-report=term-missing --cov-fail-under=80
```

Tes menggunakan database SQLite in-memory, fixture Pytest, dan dependency override FastAPI. Database pengujian tidak menggunakan database pengembangan.

## Modul KRS (Minggu 5)

### Format semester
Semester disimpan sebagai lima karakter: `YYYY1` untuk semester ganjil dan `YYYY2` untuk semester genap. Format ini menjaga pengurutan leksikografis sama dengan urutan semester. KRS hanya dapat dibuat untuk NIM yang sudah ada pada `calon_mahasiswa.nim` (mahasiswa yang telah di-approve).

### Tabel dan constraint
- `matakuliah`: kode, nama, SKS (1–4), hari (1=Senin sampai 6=Sabtu), jam mulai dan selesai.
- `krs`: satu kartu per NIM per semester; status awal `draft`.
- `krs_detail`: mata kuliah di dalam kartu, nilai nullable untuk hasil akhir semester.
- `prerequisite`: tabel penghubung self-referencing antara mata kuliah dan prasyarat.
- `skala_nilai`: pemetaan nilai huruf ke bobot dan status lulus. Seed nilai A=4, B=3, C=2 (lulus), D=1 dan E=0 (tidak lulus).

Unique constraint pada `(nim, semester)` dan `(krs_id, kode_mk)` sekaligus menyediakan indeks untuk pencarian yang sesuai. Primary key gabungan `prerequisite(kode_mk, kode_prasyarat)` melindungi pasangan prasyarat dari duplikasi.

### Chain of Responsibility
Urutan implementasi dipilih `Duplicate → SKS → Prerequisite → Conflict`. Duplikasi ditempatkan pertama karena pemeriksaannya murah dan tidak membutuhkan query tambahan. Rantai berhenti pada kegagalan pertama untuk `add_course`. `validate_krs` mengumpulkan kesalahan dari seluruh mata kuliah pada kartu. Keputusan ini juga dicatat dalam `docs/ADR-001-krs-validation.md`.

Bentrok jadwal diperiksa dengan irisan interval: hari sama, `mulai_A < selesai_B`, dan `mulai_B < selesai_A`. Karena menggunakan operator `<`, dua kelas yang bersambung tepat pada batas waktu tidak dianggap bentrok.

### Endpoint KRS Minggu 5
| Method | Endpoint | Fungsi |
|---|---|---|
| POST | `/api/krs/{nim}/{semester}/courses` | Tambah mata kuliah; body `{"kode_mk":"IF101"}` |
| DELETE | `/api/krs/{nim}/{semester}/courses/{kode_mk}` | Hapus mata kuliah |
| GET | `/api/krs/{nim}/{semester}/validate` | Validasi seluruh KRS |
| GET | `/api/krs/{nim}/{semester}` | Lihat isi dan total SKS |

`semester` harus berbentuk `YYYY1` (ganjil) atau `YYYY2` (genap). `add_course` dan `remove_course` hanya dapat mengubah KRS berstatus `draft` atau `revision`. Minggu 5 belum mengimplementasikan transisi state machine `submit`/`approve`; bagian tersebut dikerjakan pada Minggu 6.

### Query prasyarat dan bukti indeks
Query aplikasi menggunakan `NOT EXISTS` terhadap riwayat KRS mahasiswa dan `skala_nilai.bobot >= 2` dengan `lulus = true`; nilai huruf tidak dibandingkan sebagai string. Untuk memeriksa rencana query SQLite pada database yang telah dimigrasikan dan di-seed, jalankan:

```sql
EXPLAIN QUERY PLAN
SELECT m.nama
FROM prerequisite p
JOIN matakuliah m ON m.kode_mk = p.kode_prasyarat
WHERE p.kode_mk = 'IF201'
  AND NOT EXISTS (
    SELECT 1
    FROM krs_detail kd
    JOIN krs k ON k.id = kd.krs_id
    JOIN skala_nilai sn ON sn.nilai = kd.nilai
    WHERE k.nim = 'NIM_MAHASISWA'
      AND k.semester < '20261'
      AND kd.kode_mk = p.kode_prasyarat
      AND sn.lulus = 1 AND sn.bobot >= 2
  );
```

Perhatikan `SEARCH ... USING INDEX` dibandingkan `SCAN` pada hasil. Unique constraint menyediakan indeks pada pasangan NIM-semester dan KRS ID-kode MK; primary key prerequisite mengindeks kode MK pada posisi pertama. Hasil EXPLAIN bergantung pada ukuran dan statistik database, sehingga bukti aktual harus diambil dari database pengujian/pengembangan yang digunakan. SQLite EXPLAIN tidak membuktikan row locking MySQL.

### Transaksi dan row lock
Pada database yang mendukungnya, KRS dibaca dengan `SELECT ... FOR UPDATE`. SQLite mengabaikan `FOR UPDATE`, sehingga kode memakai `BEGIN IMMEDIATE` untuk menserialisasi penulis. Validasi dan insert detail dilakukan dalam satu transaksi; commit hanya dilakukan setelah validasi berhasil. Pengujian SQLite tidak dapat membuktikan row-level lock MySQL/InnoDB.

## Migration

Migration `0001_initial` membuat tabel dasar PMB, `0002_nim_counter` menambahkan counter NIM, dan `0003_krs_module` menambahkan skema KRS.

Database baru:
```bash
alembic upgrade head
```

Database Minggu 3 yang tabel-tabelnya sudah ada tetapi tabel `alembic_version` kosong (seperti kondisi database yang ditemukan pada arsip awal):
1. Cadangkan `pmb.db` terlebih dahulu.
2. Tandai skema lama sebagai revisi awal, tanpa membuat ulang tabel:
```bash
alembic stamp 0001_initial
```
3. Terapkan migration counter:
```bash
alembic upgrade head
```

Jangan menjalankan `alembic stamp` pada database kosong. Untuk database kosong, langsung gunakan `alembic upgrade head`.

Untuk menguji rollback pada database khusus, gunakan konfigurasi database uji dan jangan melakukan downgrade pada database yang berisi data penting.

Contoh hasil `EXPLAIN QUERY PLAN` dari SQLite setelah migration dan seed pada project ini menunjukkan penggunaan indeks:

```text
SEARCH p USING COVERING INDEX sqlite_autoindex_prerequisite_1 (kode_mk=?)
SEARCH k USING COVERING INDEX sqlite_autoindex_krs_1 (nim=? AND semester<?)
SEARCH kd USING INDEX sqlite_autoindex_krs_detail_1 (krs_id=? AND kode_mk=?)
SEARCH sn USING INDEX sqlite_autoindex_skala_nilai_1 (nilai=?)
SEARCH m USING INDEX sqlite_autoindex_matakuliah_1 (kode_mk=?)
```

Ini merupakan bukti rencana query pada SQLite lokal hasil seed, bukan jaminan rencana yang sama pada MySQL atau database produksi.
