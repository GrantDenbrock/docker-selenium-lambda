FROM public.ecr.aws/lambda/python@sha256:ce32e747dd996dc402c3a68ac5ce3ac116ab470c56b1275907a262137f92a52d as build
RUN yum install -y unzip && \
    curl -Lo "/tmp/chromedriver.zip" "https://chromedriver.storage.googleapis.com/104.0.5112.79/chromedriver_linux64.zip" && \
    curl -Lo "/tmp/chrome-linux.zip" "https://www.googleapis.com/download/storage/v1/b/chromium-browser-snapshots/o/Linux_x64%2F1012728%2Fchrome-linux.zip?alt=media" && \
    unzip /tmp/chromedriver.zip -d /opt/ && \
    unzip /tmp/chrome-linux.zip -d /opt/

FROM public.ecr.aws/lambda/python@sha256:ce32e747dd996dc402c3a68ac5ce3ac116ab470c56b1275907a262137f92a52d
RUN yum install atk cups-libs gtk3 libXcomposite alsa-lib \
    libXcursor libXdamage libXext libXi libXrandr libXScrnSaver \
    libXtst pango at-spi2-atk libXt xorg-x11-server-Xvfb \
    xorg-x11-xauth dbus-glib dbus-glib-devel -y \

RUN pip install selenium
RUN pip install requests
RUN pip install retrying
RUN pip install boto3
RUN pip install pandas
RUN pip install numpy
RUN pip install openpyxl
RUN pip install pymysql


COPY --from=build /opt/chrome-linux /opt/chrome
COPY --from=build /opt/chromedriver /opt/
COPY main.py ./
CMD [ "main.handler" ]
