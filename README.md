# Spider-Man: Web of Shadows Translation Tool
Bu araç, Spider-Man: Web of Shadows oyununun kaynak dosyalarını (`.PCPACK`) analiz ederek çeviriye hazır bir JSON formatına getirmek ve çevrilen metinleri LZO sıkıştırmasıyla tekrar oyuna entegre etmek için geliştirilmiştir.

## 🛠️ Gereksinimler
Bu scriptlerin sorunsuz çalışması için aşağıdaki araçların ve kütüphanelerin sisteminizde kurulu olması gerekmektedir:
* **Python 3.x**
* **Python LZO Kütüphanesi:** Sıkıştırma işlemi için gereklidir. Windows kullanıcılarının MSYS2/MinGW64 üzerinden Python kurması ve kullanması tavsiye edilir.
* **QuickBMS:** Dosyaları ilk aşamada çıkartmak için gereklidir. [QuickBMS Websitesi](http://aluigi.altervista.org/quickbms.htm) üzerinden indirebilirsiniz.
* **Spider-Man PCPACK Script:** QuickBMS ile kullanılacak `.bms` dosyası. [Buradan indirebilirsiniz](https://aluigi.altervista.org/bms/spiderman_pcpack_nch.bms).

## 🚀 Adım Adım Kullanım (Workflow)

### Adım 0: Başlangıç
Scriptleri indirin ve scriptleri indirdiğiniz klasörü terminalde açınız.

### Adım 1: Dosyaları Çıkartma
QuickBMS programını ve indirdiğiniz `.bms` scriptini kullanarak oyunun orijinal `GLOBALTEXT_ENGLISH.PCPACK` dosyasını açın. Çıkan ham dosyayı scriptlerle aynı klasöre alın ve adının `GLOBALTEXT_ENGLISH` olduğundan emin olun.

### Adım 2: Metinleri JSON Formatına Dönüştürme
Ham dosyanın içindeki metinleri çevrilebilir bir formata getirmek için aşağıdaki komutu çalıştırın:

```bash
python wos_lang_editor_v3.py extract GLOBALTEXT_ENGLISH strings.json
```
*Bu işlem sonucunda aynı dizinde, orijinal ve çevrilecek kısımları ayrı ayrı barındıran bir `strings.json` dosyası oluşacaktır.*

### Adım 3: Çeviri İşlemi
Oluşan `strings.json` dosyasını herhangi bir metin editörü ile açın. Dosya içerisindeki `"translated"` anahtarlarının karşısına kendi çevirinizi yazın ve kaydedin. (Max_len değerini aşmamaya, orijinal metin yapısını ve ID'leri bozmamaya dikkat edin).

### Adım 4: Çeviriyi Dosyaya Geri Yazma (Import)
Çeviri işleminiz bittikten sonra, bu verileri yeni bir ham dosya olarak paketlemek için şu komutu kullanın:

```bash
python wos_lang_editor_v3.py import_expanded GLOBALTEXT_ENGLISH strings.json output_test.bin
```

### Adım 5: Oyuna Hazır Hale Getirme (Compression)
Son olarak, oluşturduğumuz ham dosyayı oyunun okuyabileceği `.PCPACK` formatına geri sıkıştırmamız gerekiyor. (Eğer Windows'ta MSYS2 kullanıyorsanız, komutun başına MSYS2 Python yolunu eklemelisiniz):

```bash
C:\msys64\mingw64\bin\python.exe compress_pcpack.py output_test.bin GLOBALTEXT_ENGLISH.PCPACK
```

🎉 **İşlem Tamam!** Oluşan yeni `GLOBALTEXT_ENGLISH.PCPACK` dosyasını oyunun kurulu olduğu dizindeki orijinal dosya ile değiştirerek çevirinizi test edebilirsiniz. (İşlem öncesi orijinal dosyanın yedeğini almayı unutmayın).
