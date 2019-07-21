# adb_ganker
em......

# adb setup
first, adb server of mumu is 127.0.0.1:7555

execute this: 

`adb connect 127.0.0.1:7555`

get transport id of mumu: 

`adb devices -l`


# code setup

`adb = ADB(transid, local_tmp_dir, android_share_dir, local_share_dir)`
  
if no share dir, set local_share_dir to None

extract feature(please backup old features before run, I can't update now, I do "overwrite"):

```
adb.extract_pic("D:\\zzzj\\1\\features")
ec = ExtractConf()
ec.extract_conf("D:\\zzzj\\1\\features")
```

run:

```
matcher = Matcher("D:\\zzzj\\1\\features")
while True:
    img = adb.get_screenshot_fast()
    click = matcher.match_confs(img)
    if click is not None:
        adb.tap(click[0], click[1])
    time.sleep(1.0)
```
