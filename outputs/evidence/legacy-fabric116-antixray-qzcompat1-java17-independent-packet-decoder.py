"""Independent offline 1.16 no-span bit-array decode; no Java or network."""
import hashlib,json,pathlib,struct
BASE=pathlib.Path(r'E:\CodexTemp\QiZhangVerdict\legacy-fabric-antixray')
DATA=pathlib.Path(r'E:\CodexTemp\QiZhangVerdict\legacy-protocol-qa\node_modules\minecraft-data\minecraft-data\data\pc\1.16.2\blocks.json')
blocks=json.loads(DATA.read_text(encoding='utf-8'))
def name(state):
    return next(b['name'] for b in blocks if b['minStateId']<=state<=b['maxStateId'])
def sha(raw):return hashlib.sha256(raw).hexdigest()
reports=[]
for runid in ['02','04']:
    run=BASE/f'fabric-1.16.5-antixray-qzcompat1-java17-{runid}'
    p=run/'evidence/sent-chunk-0-0.bin';raw=p.read_bytes()
    meta=json.loads((run/'evidence/sent-chunk-0-0.json').read_text(encoding='utf-8'))
    at=0;sections={}
    def varint():
        global at
        v=shift=0
        for _ in range(5):
            b=raw[at];at+=1;v|=(b&127)<<shift
            if not b&128:return v
            shift+=7
        raise ValueError('oversize varint')
    for sy in range(16):
        if not meta['bitMap']>>sy&1:continue
        count=struct.unpack_from('>h',raw,at)[0];at+=2
        bits=raw[at];at+=1;assert 4<=bits<=16 and 0<=count<=4096
        palette=[varint() for _ in range(varint())] if bits<=8 else None
        longs_count=varint();words=struct.unpack_from('>'+str(longs_count)+'Q',raw,at);at+=longs_count*8
        assert longs_count==(4096+(64//bits)-1)//(64//bits)
        sections[sy]=(bits,palette,words)
    checks=[]
    for item in meta['positions']:
        x,y,z=[item['position'][k] for k in ['x','y','z']]
        index=(y&15)*256+z*16+x
        bits,palette,words=sections[y>>4]
        value=(words[index//(64//bits)]>>(index%(64//bits)*bits))&((1<<bits)-1)
        state=palette[value] if palette else value
        actual=name(state)
        assert actual==item['expected']==item['actual']
        checks.append({'position':item['position'],'role':item['role'],'stateId':state,'block':actual,'expected':item['expected']})
    assert not any(raw[at:]),'Unexpected nonzero trailing bytes'
    reports.append({'run':run.name,'sourcePacketSha256':sha(raw),'packetBytes':len(raw),'decodedBytes':at,'zeroPaddingBytes':len(raw)-at,'bitMap':meta['bitMap'],
                    'method':'Independent Python big-endian palette/64-bit no-span array decoder, not prismarine-chunk',
                    'allFourCoordinatesConfirmed':True,'positions':checks})
report={'schemaVersion':1,'status':'OFFLINE_SAVED_PACKET_RECHECK_PASS','javaStarted':False,'networkStarted':False,
        'blockStateDictionarySha256':sha(DATA.read_bytes()),'decoderSha256':sha(pathlib.Path(__file__).read_bytes()),'cases':reports}
(BASE/'compat-independent-chunk-recheck.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
