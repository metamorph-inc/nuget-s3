"""
"""
import re
import zipfile
import xml.etree.ElementTree
import six
import boto3
import botocore
from flask import Flask, Response, abort, send_file
from cgi import escape

app = Flask(__name__)

s3_client = boto3.client('s3')
s3_bucket = 'nuget-packages.metamorphsoftware.com'

@app.route("/")
def root():
    return "Nuget store"

@app.route('/$metadata')
def metadata():
    return r'''<edmx:Edmx xmlns:edmx="http://schemas.microsoft.com/ado/2007/06/edmx" Version="1.0">
<edmx:DataServices xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata" m:DataServiceVersion="2.0" m:MaxDataServiceVersion="2.0">
<Schema xmlns="http://schemas.microsoft.com/ado/2006/04/edm" Namespace="NuGetGallery.OData">
<EntityType Name="V2FeedPackage" m:HasStream="true">
<Key>
<PropertyRef Name="Id"/>
<PropertyRef Name="Version"/>
</Key>
<Property Name="Id" Type="Edm.String" Nullable="false"/>
<Property Name="Version" Type="Edm.String" Nullable="false"/>
<Property Name="NormalizedVersion" Type="Edm.String"/>
<Property Name="Authors" Type="Edm.String"/>
<Property Name="Copyright" Type="Edm.String"/>
<Property Name="Created" Type="Edm.DateTime" Nullable="false"/>
<Property Name="Dependencies" Type="Edm.String"/>
<Property Name="Description" Type="Edm.String"/>
<Property Name="DownloadCount" Type="Edm.Int32" Nullable="false"/>
<Property Name="GalleryDetailsUrl" Type="Edm.String"/>
<Property Name="IconUrl" Type="Edm.String"/>
<Property Name="IsLatestVersion" Type="Edm.Boolean" Nullable="false"/>
<Property Name="IsAbsoluteLatestVersion" Type="Edm.Boolean" Nullable="false"/>
<Property Name="IsPrerelease" Type="Edm.Boolean" Nullable="false"/>
<Property Name="Language" Type="Edm.String"/>
<Property Name="LastUpdated" Type="Edm.DateTime" Nullable="false"/>
<Property Name="Published" Type="Edm.DateTime" Nullable="false"/>
<Property Name="PackageHash" Type="Edm.String"/>
<Property Name="PackageHashAlgorithm" Type="Edm.String"/>
<Property Name="PackageSize" Type="Edm.Int64" Nullable="false"/>
<Property Name="ProjectUrl" Type="Edm.String"/>
<Property Name="ReportAbuseUrl" Type="Edm.String"/>
<Property Name="ReleaseNotes" Type="Edm.String"/>
<Property Name="RequireLicenseAcceptance" Type="Edm.Boolean" Nullable="false"/>
<Property Name="Summary" Type="Edm.String"/>
<Property Name="Tags" Type="Edm.String"/>
<Property Name="Title" Type="Edm.String"/>
<Property Name="VersionDownloadCount" Type="Edm.Int32" Nullable="false"/>
<Property Name="MinClientVersion" Type="Edm.String"/>
<Property Name="LastEdited" Type="Edm.DateTime"/>
<Property Name="LicenseUrl" Type="Edm.String"/>
<Property Name="LicenseNames" Type="Edm.String"/>
<Property Name="LicenseReportUrl" Type="Edm.String"/>
</EntityType>
</Schema>
<Schema xmlns="http://schemas.microsoft.com/ado/2006/04/edm" Namespace="NuGetGallery">
<EntityContainer Name="V2FeedContext" m:IsDefaultEntityContainer="true">
<EntitySet Name="Packages" EntityType="NuGetGallery.OData.V2FeedPackage"/>
<FunctionImport Name="Search" ReturnType="Collection(NuGetGallery.OData.V2FeedPackage)" EntitySet="Packages">
<Parameter Name="searchTerm" Type="Edm.String" FixedLength="false" Unicode="false"/>
<Parameter Name="targetFramework" Type="Edm.String" FixedLength="false" Unicode="false"/>
<Parameter Name="includePrerelease" Type="Edm.Boolean" Nullable="false"/>
</FunctionImport>
<FunctionImport Name="FindPackagesById" ReturnType="Collection(NuGetGallery.OData.V2FeedPackage)" EntitySet="Packages">
<Parameter Name="id" Type="Edm.String" FixedLength="false" Unicode="false"/>
</FunctionImport>
<FunctionImport Name="GetUpdates" ReturnType="Collection(NuGetGallery.OData.V2FeedPackage)" EntitySet="Packages">
<Parameter Name="packageIds" Type="Edm.String" FixedLength="false" Unicode="false"/>
<Parameter Name="versions" Type="Edm.String" FixedLength="false" Unicode="false"/>
<Parameter Name="includePrerelease" Type="Edm.Boolean" Nullable="false"/>
<Parameter Name="includeAllVersions" Type="Edm.Boolean" Nullable="false"/>
<Parameter Name="targetFrameworks" Type="Edm.String" FixedLength="false" Unicode="false"/>
<Parameter Name="versionConstraints" Type="Edm.String" FixedLength="false" Unicode="false"/>
</FunctionImport>
</EntityContainer>
</Schema>
</edmx:DataServices>
</edmx:Edmx>'''


@app.route('/FindPackagesById()')
def FindPackagesById():
    ''' ?id='id' '''
    ret = r'''<?xml version="1.0" ?>
<feed xml:base="http://www.nuget.org/api/v2" xmlns="http://www.w3.org/2005/Atom" xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices" xmlns:georss="http://www.georss.org/georss" xmlns:gml="http://www.opengis.net/gml" xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata">
	<m:count>0</m:count>
	<id>http://schemas.datacontract.org/2004/07/</id>
	<title/>
	<updated>2017-05-18T18:51:51Z</updated>
	<link href="http://www.nuget.org/api/v2/Packages" rel="self"/>
	<author>
		<name/>
	</author>
</feed>'''

    return Response(ret, mimetype='application/atom+xml')


@app.route('/<path:path>')
def route(path):
    # print(path)
    if path.startswith('Packages(Id='):
        return metadata(path)
    if path.endswith('.nupkg'):
        return package(path)
    return abort(404)


def package(path):
    buffer = six.BytesIO()
    s3_client.download_fileobj(s3_bucket, path, buffer)
    buffer.seek(0)
    # TODO last_modified=
    return send_file(buffer, mimetype='application/zip')

def metadata(path):
    buffer = six.BytesIO()
    package, version = re.match(r"Packages\(Id='(.*)',Version='(.*)'.*\)", path).groups()
    try:
        s3_client.download_fileobj(s3_bucket, '{}.{}.nupkg'.format(package, version), buffer)
    except botocore.exceptions.ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            return abort(404)
        raise
    buffer.seek(0)
    with zipfile.ZipFile(buffer, 'r', allowZip64=True) as zip:
        e = xml.etree.ElementTree.parse(six.BytesIO(zip.read('{}.nuspec'.format(package)))).getroot()
        metadata = {re.sub('{.*?}', '', el.tag): escape(el.text) for el in e.find('{http://schemas.microsoft.com/packaging/2011/10/nuspec.xsd}metadata')}
        # {'projectUrl': 'https://svn.isis.vanderbilt.edu/META/trunk', 'owners': 'ksmyth', 'requireLicenseAcceptance': 'false', 'description': 'CadCreoParametricCreateAssembly',
        # 'copyright': 'Copyright 2013 ISIS, Vanderbilt University', 'title': 'CadCreoParametricCreateAssembly', 'releaseNotes': 'Initial release', 'iconUrl': 'http://repo.isis.vanderbilt.edu/GME/GME.ico',
        # 'version': '1.5.15.45-gita34e3610', 'licenseUrl': 'https://svn.isis.vanderbilt.edu/META/trunk/license.txt', 'authors': 'ISIS, Vanderbilt University', 'id': 'META.CadCreoParametricCreateAssembly'}
    metadata['s3_bucket'] = s3_bucket
    ret = (r'''<?xml version="1.0" ?>
<entry xml:base="https://www.nuget.org/api/v2" xmlns="http://www.w3.org/2005/Atom" xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices" xmlns:georss="http://www.georss.org/georss" xmlns:gml="http://www.opengis.net/gml" xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata">
	<id>https://www.nuget.org/api/v2/Packages(Id='{id}',Version='{version}')</id>
	<category scheme="http://schemas.microsoft.com/ado/2007/08/dataservices/scheme" term="NuGetGallery.OData.V2FeedPackage"/>
	<link href="https://www.nuget.org/api/v2/Packages(Id='{id}',Version='{version}')" rel="edit"/>
	<link href="https://www.nuget.org/api/v2/Packages(Id='{id}',Version='{version}')" rel="self"/>
	<title type="text">{id}</title>
	<summary type="text">{description}</summary>
	<updated>2000-01-01T01:01:01Z</updated>
	<author>
		<name>{authors}</name>
	</author>
	<content src="https://{s3_bucket}/{id}.{version}.nupkg" type="application/zip"/>
	<m:properties>
		<d:Id>{id}</d:Id>
		<d:Version>{version}</d:Version>
		<d:NormalizedVersion>{version}</d:NormalizedVersion>
		<d:Authors>{authors}</d:Authors>
		<d:Copyright>{copyright}</d:Copyright>
		<d:Created m:type="Edm.DateTime">2000-01-01T01:01:01Z</d:Created>
		<d:Dependencies></d:Dependencies>
		<d:Description>{description}</d:Description>
		<d:DownloadCount m:type="Edm.Int32">1</d:DownloadCount>
		<d:GalleryDetailsUrl>https://www.nuget.org/packages/{id}/{version}</d:GalleryDetailsUrl>
		<d:IconUrl>{iconUrl}</d:IconUrl>
		<d:IsLatestVersion m:type="Edm.Boolean">true</d:IsLatestVersion>
		<d:IsAbsoluteLatestVersion m:type="Edm.Boolean">true</d:IsAbsoluteLatestVersion>
		<d:IsPrerelease m:type="Edm.Boolean">false</d:IsPrerelease>
		<d:Language m:null="true"/>
		<d:LastUpdated m:type="Edm.DateTime">2000-01-01T01:01:01Z</d:LastUpdated>
		<d:Published m:type="Edm.DateTime">2000-01-01T01:01:01Z</d:Published>''' +
		# <d:PackageHash>O5SaKtrHoZwyL9xMi1Q/Buaz7kjLE3E3Q4q//fZGnaaJ/sNMUM0jK5WYgqyFJvv2K4DjpJHJ7eAW/bJQ+aXmdg==</d:PackageHash>
		# <d:PackageHashAlgorithm>SHA512</d:PackageHashAlgorithm>
		# <d:PackageSize m:type="Edm.Int64">87671</d:PackageSize>
		# <d:ReportAbuseUrl>https://www.nuget.org/packages/{id}/{version}/ReportAbuse</d:ReportAbuseUrl>
		r'''<d:ProjectUrl>http://{id}.sourceforge.net/</d:ProjectUrl>
		<d:ReleaseNotes>{releaseNotes}</d:ReleaseNotes>
		<d:RequireLicenseAcceptance m:type="Edm.Boolean">false</d:RequireLicenseAcceptance>
		<d:Summary>{description}</d:Summary>
		<d:Tags></d:Tags>
		<d:Title>{id}</d:Title>
		<d:VersionDownloadCount m:type="Edm.Int32">2</d:VersionDownloadCount>
		<d:MinClientVersion m:null="true"/>
		<d:LastEdited m:null="true"/>
		<d:LicenseUrl>{licenseUrl}</d:LicenseUrl>
		<d:LicenseNames m:null="true"/>
		<d:LicenseReportUrl m:null="true"/>
        </m:properties>
    </entry>
    ''').format(**metadata)
    return Response(ret, mimetype='application/atom+xml')

if __name__ == "__main__":
    # app.run()
    app.run(port=5000, debug=True, host='0.0.0.0', use_reloader=False)
