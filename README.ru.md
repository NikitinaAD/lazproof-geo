# lazproof-geo

`lazproof` доказывает, что результат LAS/LAZ является точным пространственным
подмножеством исходного файла с сохранением порядка точек и всех измерений.

```bash
lazproof verify source.laz clipped.laz --inside boundary.geojson --report proof.json
```

Инструмент не выполняет обрезку и не зависит от PDAL. Он потоково проверяет все
размерности, Extra Bytes, формат точек, версию LAS, CRS, масштабы и смещения.

Copyright 2026 Alena Nikitina. Apache License 2.0.

