"""Independent APK v2 signature/digest verification for the repository debug APK.
Not a substitute for Android installation/OS verifier, nor Play Store release validation.
"""
import hashlib,json,struct,sys,zipfile
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import padding

def lp4(b, at=0):
 if at+4>len(b):raise ValueError('SHORT_LP')
 n=struct.unpack_from('<I',b,at)[0]
 if at+4+n>len(b):raise ValueError('BAD_LP')
 return b[at+4:at+4+n],at+4+n

def verify(path):
 p=Path(path); b=p.read_bytes(); z=zipfile.ZipFile(p)
 if z.testzip() is not None:raise ValueError('ZIP_CRC_FAIL')
 eocd=b.rfind(b'PK\x05\x06')
 if eocd<0:raise ValueError('NO_EOCD')
 cd_off=struct.unpack_from('<I',b,eocd+16)[0]
 if b[cd_off-16:cd_off]!=b'APK Sig Block 42':raise ValueError('NO_V2_BLOCK')
 size=struct.unpack_from('<Q',b,cd_off-24)[0]
 start=cd_off-size-8
 if start<0 or struct.unpack_from('<Q',b,start)[0]!=size:raise ValueError('BLOCK_LENGTH')
 at=start+8
 pairlen=struct.unpack_from('<Q',b,at)[0];at+=8
 pairid=struct.unpack_from('<I',b,at)[0];at+=4
 if pairid!=0x7109871a:raise ValueError('NO_V2_PAIR')
 if at+pairlen-4!=cd_off-24:raise ValueError('PAIR_LENGTH')
 v2=b[at:at+pairlen-4]
 v2_signers,_=lp4(v2)
 signer,_=lp4(v2_signers)
 sd,at=lp4(signer)
 signs,at=lp4(signer,at)
 pub,at=lp4(signer,at)
 signed_digests,t=lp4(sd)
 certs,t=lp4(sd,t)
 d_item,_=lp4(signed_digests)
 alg=struct.unpack_from('<I',d_item,0)[0]
 digest,_=lp4(d_item,4)
 sig_item,_=lp4(signs)
 salg=struct.unpack_from('<I',sig_item,0)[0]
 signature,_=lp4(sig_item,4)
 cert_der,_=lp4(certs)
 cert=x509.load_der_x509_certificate(cert_der)
 if alg!=salg or alg!=0x0103:raise ValueError('UNSUPPORTED_ALGORITHM')
 actual_pub=cert.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)
 if actual_pub!=pub:raise ValueError('PUBKEY_MISMATCH')
 cert.public_key().verify(signature,sd,padding.PKCS1v15(),hashes.SHA256())
 new_eocd=bytearray(b[eocd:]);struct.pack_into('<I',new_eocd,16,start)
 pieces=(b[:start],b[cd_off:eocd],bytes(new_eocd))
 chunks=[]
 for section in pieces:
  for i in range(0,len(section),1<<20):
   chunk=section[i:i+(1<<20)];chunks.append(hashlib.sha256(b'\xa5'+struct.pack('<I',len(chunk))+chunk).digest())
 result=hashlib.sha256(b'\x5a'+struct.pack('<I',len(chunks))+b''.join(chunks)).digest()
 if result!=digest:raise ValueError('CONTENT_DIGEST_MISMATCH')
 manifest=z.read('AndroidManifest.xml')
 if b'android.permission.INTERNET' in manifest:raise ValueError('UNEXPECTED_INTERNET')
 return {'status':'PASS','zip_crc':'PASS','v2_signature':'PASS','v2_content_digest':'PASS','cert_public_key_match':'PASS',
         'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'permission_internet':False,
         'assets_domain_js': 'assets/www/dmsg-domainintel.js' in z.namelist(),
         'android_runtime':'NOT_RUN','debug_signed':True,'files':len(z.namelist())}
if __name__=='__main__': print(json.dumps(verify(sys.argv[1]),indent=2))
