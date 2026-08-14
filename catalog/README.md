# Equipment catalog

Plain CSV, one file per brand, read fresh on every request. Edit a file, reload the
editor, and the new rows are in the Make / Model / License dropdowns — no restart.

```text
catalog/
  cameras/Hanwha.csv     # the models offered under the make "Hanwha"
  cameras/Generic.csv    # a warning-free placeholder for an unspecified camera
  licenses/Hanwha.csv    # the licenses offered alongside that make (optional)
```

**The file name is the make.** Adding a vendor means adding `cameras/Axis.csv`; the
name appears in the Make dropdown exactly as the file is named. A brand with no
`licenses/<Brand>.csv` simply has no License dropdown.

## cameras/&lt;Make&gt;.csv

| Column       | Required | Shown as                                       |
| ------------ | -------- | ---------------------------------------------- |
| `model`      | yes      | the option itself, and what gets saved         |
| `series`     | no       | the group heading the model is listed under    |
| `type`       | no       | subtext — Dome, Bullet, Flateye, Fisheye, …    |
| `resolution` | no       | subtext — 8MP, 5MP, …                          |
| `fov`        | no       | subtext — `113°-47°` for a varifocal lens      |

`resolution`, `fov` and `type` are joined into the one grey line under the model name,
separated by central dots. Any of them may be left blank.

## licenses/&lt;Make&gt;.csv

| Column   | Required | Shown as                            |
| -------- | -------- | ----------------------------------- |
| `sku`    | yes      | the option itself, and what is saved |
| `name`   | no       | the readable name beside the SKU     |
| `detail` | no       | the grey subtext line                |

## House rules

- Keep the files UTF-8. The degree sign in `fov` is the only character that needs it.
- Rows are offered in file order, so keep the models you fit most often near the top.
- A duplicate `model` (or `sku`) in one file is ignored after its first appearance.
- Saved plans keep whatever make/model text they were given. Removing a row here does
  not rewrite existing plans — those cameras keep showing their old model.
- Keep `Generic camera` available for placements that intentionally do not need a quoted
  model. Unlike a blank model, choosing it marks the equipment decision as complete.
