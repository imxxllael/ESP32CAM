import numpy as np
import cv2 as cv
import Person
import time
import urllib.request


try:
    log = open('log.txt',"w")
except:
    print( "Cannot open log file")

#Entry and exit counters
cnt_up   = 0
cnt_down = 0

#Source of video
##cap = cv.VideoCapture(0)
##cap = cv.VideoCapture('Test Files/TestVideo/test.mp4')
#camera = PiCamera()
##camera.resolution = (160,120)
##camera.framerate = 5
##rawCapture = PiRGBArray(camera, size=(160,120))
##time.leep(0.1)
url = "http://192.168.1.23"
#cap = cv.VideoCapture(url)

#video properties
##cap.set(3,160) #Width
##cap.set(4,120) #Height

#Print the capture properties to console
for i in range(19):

    h = 600
w = 1500
frameArea = h*w
areaTH = frameArea/200
print( 'Area Threshold', areaTH)

#input/output lines
line_up = int(3*(h/5))
line_down   = int(2*(h/5))

up_limit =   int(1*(h/5))
down_limit = int(4*(h/5))

print( "Red line y:",str(line_down))
print( "Blue line y:", str(line_up))
line_down_color = (255,0,0)
line_up_color = (0,0,255)
pt1 =  [0, line_down];
pt2 =  [w, line_down];
pts_L1 = np.array([pt1,pt2], np.int32)
pts_L1 = pts_L1.reshape((-1,1,2))
pt3 =  [0, line_up];
pt4 =  [w, line_up];
pts_L2 = np.array([pt3,pt4], np.int32)
pts_L2 = pts_L2.reshape((-1,1,2))

pt5 =  [0, up_limit];
pt6 =  [w, up_limit];
pts_L3 = np.array([pt5,pt6], np.int32)
pts_L3 = pts_L3.reshape((-1,1,2))
pt7 =  [0, down_limit];
pt8 =  [w, down_limit];
pts_L4 = np.array([pt7,pt8], np.int32)
pts_L4 = pts_L4.reshape((-1,1,2))

#background subtractor
fgbg = cv.createBackgroundSubtractorMOG2(detectShadows = True)

#Structuring elements for morphological filters
kernelOp = np.ones((4,3),np.uint8)
kernelOp2 = np.ones((4,5),np.uint8)
kernelCl = np.ones((11,11),np.uint8)

#Variables
font = cv.FONT_HERSHEY_SIMPLEX
persons = []
max_p_age = 5
pid = 1

while True:
    img_resp = urllib.request.urlopen(url)
    img_np = np.array(bytearray(img_resp.read()), dtype=np.uint8)
    frame = cv.imdecode(img_np, -1)
    
    if frame is not None:
        for i in persons:
            i.age_one() #age every person one frame

        fgmask = fgbg.apply(frame)
        fgmask2 = fgbg.apply(frame)

    #########################
    #   PRE-PROCESSING      #
    #########################
    
    #Apply background subtraction
    fgmask = fgbg.apply(frame)
    fgmask2 = fgbg.apply(frame)

    #Binary to remove shadows (gray color)
    try:
        ret,imBin= cv.threshold(fgmask,220,255,cv.THRESH_BINARY)
        ret,imBin2 = cv.threshold(fgmask2,220,255,cv.THRESH_BINARY)
        #Opening (erode->dilate) to remove noise.
        mask = cv.morphologyEx(imBin, cv.MORPH_OPEN, kernelOp)
        mask2 = cv.morphologyEx(imBin2, cv.MORPH_OPEN, kernelOp)
       #Closing (dilate -> erode) to close white regions together.
        mask =  cv.morphologyEx(mask , cv.MORPH_CLOSE, kernelCl)
        mask2 = cv.morphologyEx(mask2, cv.MORPH_CLOSE, kernelCl)
    except:
        print('EOF')
        print( 'Enter:',cnt_up)
        print ('Exit:',cnt_down)
        break
    #################
    #   CONTOURS   #
    #################
    
    # RETR_EXTERNAL returns only extreme outer flags. All child contours are left behind.
    contours0, hierarchy = cv.findContours(mask2,cv.RETR_EXTERNAL,cv.CHAIN_APPROX_SIMPLE)
    for cnt in contours0:
        area = cv.contourArea(cnt)
        if area > areaTH:
            #################
            #   TRACKING    #
            #################
            
            #It remains to add conditions for multi-persons, exits and screen entrances.
            
            M = cv.moments(cnt)
            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])
            x,y,w,h = cv.boundingRect(cnt)

            new = True
            if cy in range(up_limit,down_limit):
                for i in persons:
                    if abs(x-i.getX()) <= w and abs(y-i.getY()) <= h:
                        # the object is close to one that was detected before
                        new = False
                        i.updateCoords(cx,cy)   #updates coordinates on the object and resets age
                        if i.going_UP(line_down,line_up) == True:
                            cnt_up += 1;
                            print( "ID:",i.getId(),'crossed going up at',time.strftime("%c"))
                            log.write("ID: "+str(i.getId())+' crossed going up at ' + time.strftime("%c") + '\n')
                        elif i.going_DOWN(line_down,line_up) == True:
                            cnt_down += 1;
                            print( "ID:",i.getId(),'crossed going down at',time.strftime("%c"))
                            log.write("ID: " + str(i.getId()) + ' crossed going down at ' + time.strftime("%c") + '\n')
                        break
                    if i.getState() == '1':
                        if i.getDir() == 'down' and i.getY() > down_limit:
                            i.setDone()
                        elif i.getDir() == 'up' and i.getY() < up_limit:
                            i.setDone()
                    if i.timedOut():
                        #remove i from persons list
                        index = persons.index(i)
                        persons.pop(index)
                        del i     #release the memory of i
                if new == True:
                    p = Person.MyPerson(pid,cx,cy, max_p_age)
                    persons.append(p)
                    pid += 1     
            #################
            #   DRAWINGS    #
            #################
            cv.circle(frame,(cx,cy), 5, (0,0,255), -1)
            img = cv.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),2)            
            cv.drawContours(frame, cnt, -1, (0,255,0), 3)
            
    #END for cnt in contours0
            
    #########################
    # DRAW TRAJECTORIES  #
    #########################
    for i in persons:
##        if len(i.getTracks()) >= 2:
##            pts = np.array(i.getTracks(), np.int32)
##            pts = pts.reshape((-1,1,2))
##            frame = cv.polylines(frame,[pts],False,i.getRGB())
##        if i.getId() == 9:
##            print str(i.getX()), ',', str(i.getY())
        cv.putText(frame, str(i.getId()),(i.getX(),i.getY()),font,0.3,i.getRGB(),1,cv.LINE_AA)
        
    #################
    #   IMAGE       #
    #################
    str_up = 'ENTER: '+ str(cnt_up)
    str_down = 'EXIT: '+ str(cnt_down)
    frame = cv.polylines(frame,[pts_L1],False,line_down_color,thickness=2) #blueline
    frame = cv.polylines(frame,[pts_L2],False,line_up_color,thickness=2)    #Redline
    frame = cv.polylines(frame,[pts_L3],False,(255,255,255),thickness=1) #Upline_limit
    frame = cv.polylines(frame,[pts_L4],False,(255,255,255),thickness=1)    #Downline_limit
    cv.putText(frame, str_up ,(10,40),font,0.5,(255,255,255),2,cv.LINE_AA)
    cv.putText(frame, str_up ,(10,40),font,0.5,(0,0,255),1,cv.LINE_AA)
    cv.putText(frame, str_down ,(10,90),font,0.5,(255,255,255),2,cv.LINE_AA)
    cv.putText(frame, str_down ,(10,90),font,0.5,(255,0,0),1,cv.LINE_AA)

    cv.imshow('Frame',frame)
    cv.imshow('Mask',mask)    
    

##    rawCapture.truncate(0)
    #press ESC to exit 
    k = cv.waitKey(1) & 0xff #Waitkey=Motion speed
    if k == 27:
        break
#END while(cap.isOpened())
    
#################
#  CLEANING     #
#################
log.flush()
log.close()
cv.destroyAllWindows()
