# _*_ coding:UTF-8 _*_
import sys,os,platform
import time
import subprocess
import cv2
import numpy as np
import threading
import copy

class ADB(object):

    def __init__(self, trans_id, tmp_dir, remote_share, local_share):
        self.trans_id = trans_id
        self.tmp_dir = tmp_dir
        self.remote_share = remote_share
        self.local_share = local_share
        if self.local_share is None:
            self.enable_share = False
        else:
            self.enable_share = True
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)
        
    def execute_shell(self, shell):
        start = time.time()
        p = subprocess.Popen(shell, shell=True, stdout=subprocess.PIPE)
        out = p.communicate()
        end = time.time()
        print("%s cost %fs" % (shell, end - start))
        return (p.returncode, out)

    def tap(self, x, y):
        tap_ret = self.execute_shell( \
            "adb -t %d shell input tap %d %d" % (self.trans_id, x, y))
        return tap_ret[0]

    def get_screenshot(self):
        screenshot_path = self.remote_share + "/screenshot.png"
        local_path = self.tmp_dir + "\\screenshot.png"
        sc_ret = self.execute_shell( \
            "adb -t %d shell screencap %s" % (self.trans_id, screenshot_path))
        if sc_ret[0] == 0:
            if self.enable_share:
                local_path = self.local_share + "\\screenshot.png"
                img = cv2.imread(local_path)
                os.unlink(local_path)
                return img
            else:
                pull_ret = self.execute_shell( \
                    "adb -t %d pull %s %s" % (self.trans_id, screenshot_path, local_path))
                self.execute_shell("adb -t %d rm -f %s" % (self.trans_id, screenshot_path))
                if pull_ret[0] == 0:
                    img = cv2.imread(local_path)
                    return img
                else:
                    return None
        else:
            return None

    def get_screenshot_fast(self):
        if not self.enable_share:
            return self.get_screenshot()
        screenshot_path = self.remote_share + "/screenshot.raw"
        local_path = self.local_share + "\\screenshot.raw"
        sc_ret = self.execute_shell( \
            "adb -t %d shell screencap %s" % (self.trans_id, screenshot_path))
        if sc_ret[0] != 0:
            return None
        try:
            file = open(local_path, 'rb')
            try:
                image_data = file.read()
            except:
                image_data = None
            finally:
                file.close()
        except:
            print("open file %s error" % local_path, file=sys.stderr)
            image_data = None
        if image_data is None:
            return None
        width = int.from_bytes(image_data[0:4], byteorder="little")
        height = int.from_bytes(image_data[4:8], byteorder="little")
        f = int.from_bytes(image_data[8:12], byteorder="little")
        data = image_data[12:]
        # check data length
        if f != 1:
            print("picture format is not rgba[8888], not supported!", file=sys.stderr)
            return self.get_screenshot()
        if len(data) != width * height * 4:
            print("data length error w[%d] h[%d] expect_pixel[%d]" \
                  % (width, height, len(data) / 4), file=sys.stderr)
        flat_numpy_array = np.frombuffer(data, dtype=np.uint8)
        colors = flat_numpy_array.reshape(height, width, 4)
        return cv2.cvtColor(colors, cv2.COLOR_RGBA2BGR)
    
    def extract_pic(self, dir):
        if not os.path.exists(dir):
            os.mkdir(dir)
        cnt = 0
        while True:
            input_ch = input("(c$num/x): ")
            if input_ch == "x":
                break
            num = input_ch[1:]
            if len(num) == 0:
                c = 1
            else:
                c = int(num)
            print("capture dir:%s cnt:%d num:%d" % (dir, cnt, c))
            for i in range(1, c+1):
                img = self.get_screenshot_fast()
                #print(img)
                file = dir + '\\' + str(cnt) + "_" + str(i) + ".png"
                print("save %s" % file)
                cv2.imwrite(file, img)
            cnt = cnt + 1

class ExtractConf(object):
    def __init__(self):
        self.start_x = 0
        self.start_y = 0
        self.end_x = 0
        self.end_y = 0
        self.cur_img = None
        self.drawing = False

    def on_EVENT_LBUTTON(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            xy = "%d,%d" % (x, y)
            print(xy)
            self.start_x = x
            self.start_y = y
            self.drawing = True
        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
            xy = "%d,%d" % (x, y)
            print(xy)
            self.end_x = x
            self.end_y = y
            new_img = copy.deepcopy(self.cur_img)
            cv2.rectangle(new_img, (self.start_x, self.start_y), (self.end_x, self.end_y), \
                          (128, 128, 128), thickness = 1)
            cv2.imshow("image", new_img)
        elif event == cv2.EVENT_MOUSEMOVE and flags == cv2.EVENT_FLAG_LBUTTON:
            if self.drawing == True:
                new_img = copy.deepcopy(self.cur_img)
                cv2.rectangle(new_img, (self.start_x, self.start_y), (x, y), \
                              (128, 128, 128), thickness = 1)
                cv2.imshow("image", new_img)
            
    def extract_conf(self, dir):
        files = os.listdir(dir)
        prefixs = set()
        for file in files:
            res = file.split('_')
            if (len(res)) != 2:
                continue
            if not res[0].isdigit():
                continue
            prefixs.add(int(res[0]))
        prefix_list = list(prefixs)
        confs = []
        prefix_list.sort()
        cv2.namedWindow("image")
        cv2.setMouseCallback("image", self.on_EVENT_LBUTTON)
        for pre in prefix_list:
            ended = False
            cur = "%s\\%d_1.png" % (dir, pre)
            self.cur_img = cv2.imread(cur)
            shape = self.cur_img.shape
            height = shape[0]
            width = shape[1]
            self.start_x = 0
            self.start_y = 0
            self.end_x = width
            self.end_y = height
            cv2.imshow("image", self.cur_img)
            cv2.waitKey(0)
            confs.append((pre, self.start_x, self.start_y, self.end_x, self.end_y))
        cv2.destroyAllWindows()
        self.save_conf(confs, dir)

    def save_conf(self, confs, dir):
        conf_file = dir + "/config"
        f = open(conf_file, 'w')
        for c in confs:
            buf = "%d,%d,%d,%d,%d\n" % (c[0], c[1], c[2], c[3], c[4])
            f.write(buf)
        f.close()

class Matcher(object):
    def __init__(self, dir):
        confs = self.load_conf(dir)
        self.conf = self.load_imgs(confs, dir)
        
    def load_conf(self, dir):
        expand = 2
        conf_file = dir + "\\config"
        f = open(conf_file, 'r')
        content = f.read()
        conf_list = content.split("\n")
        confs = []
        for conf in conf_list:
            if len(conf) > 0:
                splits = conf.split(',')
                idx = int(splits[0])
                s_x = int(splits[1])
                s_y = int(splits[2])
                e_x = int(splits[3])
                e_y = int(splits[4])
                if e_x < s_x:
                    tmp = s_x
                    s_x = e_x
                    e_x = tmp
                if e_y < s_y:
                    tmp = s_y
                    s_y = e_y
                    e_y = tmp
                confs.append((idx, (s_x, s_y, e_x, e_y), expand))
        return confs

    def load_imgs(self, confs, dir):
        conf_index = dict()
        for c in confs:
            idx = c[0]
            rect = c[1]
            expand = c[2]
            conf_index[idx] = (rect, expand)
        files = os.listdir(dir)
        file_index = dict()
        for file in files:
            res = file.split('_')
            if (len(res)) != 2:
                continue
            if not res[0].isdigit():
                continue
            idx = int(res[0])
            if idx not in conf_index:
                continue
            cur_conf = conf_index[idx]
            cur_rect = cur_conf[0]
            if idx not in file_index:
                file_index[idx] = []
            img = cv2.imread(dir + "\\" + file)
            file_index[idx].append(img[cur_rect[1]:cur_rect[3], cur_rect[0]:cur_rect[2]])
        final_conf = []
        for c in confs:
            idx = c[0]
            if idx not in file_index:
                continue
            final_conf.append((idx, c[1], c[2], file_index[idx]))
        return final_conf

    def match(self, img, findimg):
        #cv2.imshow("image", img)
        #cv2.imshow("image2", findimg)
        w=img.shape[1]
        h=img.shape[0]
        fw=findimg.shape[1]
        fh=findimg.shape[0]
        findpt=None
        #print(h-fh)
        #print(w-fw)
        for now_h in range(0,h-fh):
            for now_w in range(0,w-fw):
                comp_tz=img[now_h:now_h+fh,now_w:now_w+fw,:] - findimg
                #print(np.mean(comp_tz))
                if abs(np.mean(comp_tz)) < 20:
                    findpt=now_w,now_h
                    print("match ok")
        return findpt

    def match_conf(self, cur_conf, img):
        w = img.shape[1]
        h = img.shape[0]
        print("matching rule %d ..." % cur_conf[0])
        expand = cur_conf[2]
        #print(expand)
        zero_x = cur_conf[1][0]
        zero_y = cur_conf[1][1]
        m_x = cur_conf[1][2]
        m_y = cur_conf[1][3]
        #print("raw:%d,%d,%d,%d" % (zero_x, zero_y, m_x, m_y))
        if zero_x - expand < 0:
            zero_x = 0
        else:
            zero_x = zero_x - expand
        if zero_x - expand > w:
            zero_x = w
        if zero_y - expand < 0:
            zero_y = 0
        else:
            zero_y = zero_y - expand
        if zero_y - expand > h:
            zero_y = h
        if m_x + expand > w:
            m_x = w
        else:
            m_x = m_x + expand
        if m_y + expand > h:
            m_y = h
        else:
            m_y = m_y + expand
        #print("exp:%d,%d,%d,%d" % (zero_x, zero_y, m_x, m_y))

        cur_croped_img = img[zero_y:m_y, zero_x:m_x]
        click = None
        for findimg in cur_conf[3]:
            find = self.match(cur_croped_img, findimg)
            if find is not None:
                click = (zero_x + find[0] + findimg.shape[1] / 2, zero_y + find[1] + findimg.shape[0] / 2)
                break
        return click

    def match_confs(self, img):
        res = None
        for conf in self.conf:
            res = self.match_conf(conf, img)
            if res is not None:
                break
        return res
    
if __name__ == "__main__":
    adb = ADB(1, "D:\\zzzj\\1", "/data/Share", "D:\\zzzj\\1\\Share")
    # match screenshot online... comment this while extract feature
    matcher = Matcher("D:\\zzzj\\1\\features1")
    while True:
        img = adb.get_screenshot_fast()
        click = matcher.match_confs(img)
        if click is not None:
            adb.tap(click[0], click[1])
        time.sleep(1.0)

    ## extract screenshots and features... comment this while match screenshot online
    #adb.extract_pic("D:\\zzzj\\1\\features1")
    #ec = ExtractConf()
    #ec.extract_conf("D:\\zzzj\\1\\features1")


