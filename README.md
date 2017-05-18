NuGet server hosted on S3/Lambda

Currently only supports `nuget.exe install -Version 1.2.3 Package` (no searches), without dependencies

C:\Python27\python -m virtualenv venv
venv\Scripts\activate
pip install -r requirements.txt
zappa deploy
openssl genrsa 2048 > account.key
zappa certify

Route 53: set nuget.metamorphsoftware.com as CNAME to deployed domain

Put packages in nuget-packages.metamorphsoftware.com and set up CloudFront for https. Set permissions: Everyone: read object.
