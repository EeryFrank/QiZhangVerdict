# SPDX-License-Identifier: GPL-3.0-only
"""Publish only an explicitly reviewed, complete 14-case file audit. No runtime execution."""
from pathlib import Path
import hashlib, json
import audit

ROOT=audit.ROOT; HERE=audit.HERE
digest=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text('utf-8'))

def exclusive_same(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        assert path.read_bytes()==data, 'Refusing to overwrite existing output: '+str(path)
    else:
        with path.open('xb') as stream: stream.write(data)

def main():
    audit.run()
    progress=read(HERE/'progress.json'); visual=read(HERE/'visual-review.json')
    assert progress['completedAuditedCases']==14 and progress['pendingCases']==[]
    assert len({c['id'] for c in progress['cases']})==14
    evidence=progress['evidence']
    for case in progress['cases']:
        assert case['passed'] and case['clientExitCode']==case['serverExitCode']==0
        case['strictDefaultSettingCount']=13
        case['strictPolicySha256']=audit.POLICY_SHA
        case['defaultRuleCount']=37
        for ref in case['evidence']: ref['publicFile']='outputs/'+ref['file']
        for png in case['pngs']: png['publicFile']='outputs/'+png['file']
        case['visualReview']=[]
        for png in case['pngs']:
            matches=[v for v in visual if v['case']==case['id'] and v['pngSha256']==png['sha256']]
            assert len(matches)==1, 'Missing explicit image review: '+case['id']
            case['visualReview'].append(matches[0])
    references=[]; artifacts={}
    for case in progress['cases']:
        for key in ('clientAndServerArtifact','clientArtifact','serverArtifact'):
            if key in case:
                value=case[key]; artifacts[value['path']]=(value['sha256'],value['bytes'])
    assert len(artifacts)==13
    for name in ('build-validation-0.2.0-test.1.json','artifact-core-validation-0.2.0-test.1.json'):
        path=ROOT/'outputs'/name
        assert path.is_file(), 'Final accepted build/core report not yet available'
        aggregate=read(path); entries=aggregate.get('artifacts',aggregate.get('cases'))
        accepted={x['artifact']['path']:(x['artifact']['sha256'],x['artifact']['bytes']) for x in entries if x['passed']}
        assert artifacts==accepted, 'Client artifact set differs from build/core aggregate'
        references.append({'file':name,'publicFile':'outputs/'+name,'sha256':digest(path),'bytes':path.stat().st_size})
    for path in (HERE/'audit.py',HERE/'finalize.py',HERE/'visual-review.json'):
        evidence.append({'file':'evidence/client-020-audit-'+path.name,'sha256':digest(path),'bytes':path.stat().st_size,
                         'category':'independent-auditor' if path.suffix=='.py' else 'visual-review','originalFiles':[str(path)],'rawBytesPreserved':True})
    assert len({x['file'] for x in evidence})==len(evidence)
    for item in evidence: item['publicFile']='outputs/'+item['file']
    history_path=HERE/'failed-attempts.json'
    # An explicit empty index means the parent confirmed no failed attempts in these fourteen final runs.
    assert history_path.exists(), 'Run owner must confirm the attempt history explicitly'
    history=read(history_path)
    assert history.get('reviewedByRunOwner') is True
    assert history['failedClientAttemptCount']==len(progress['failedAttempts'])
    for attempt in progress['failedAttempts']:
        for ref in attempt['evidence']: ref['publicFile']='outputs/'+ref['file']
    for item in evidence:
        originals=[Path(x) for x in item['originalFiles']]
        data=originals[0].read_bytes()
        assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256']
        assert all(x.read_bytes()==data for x in originals)
        exclusive_same(ROOT/'outputs'/item['file'],data)
    limits=[
      'Real rendered production clients on Windows, isolated loopback servers and controlled offline-auth accounts; no real Microsoft/Mojang account-authentication acceptance claim.',
      'Exactly the listed Minecraft/loader/Java/JAR combinations were exercised. This does not prove all Minecraft versions, modpacks, hardware, multiplayer load, long-duration behavior or public-network deployment.',
      'Each screenshot has independent PNG signature/chunk CRC/zlib/scanline/pixel checks and an explicit agent image review. One still image does not prove performance or gameplay breadth.',
      'The new 37-rule first-install defaults and unchanged 13 strict settings were checked in each fixture. No cheat binary was run; this is not a trial of every cheat or an unspoofable client/VM attestation.',
      'Device association was independently recomputed for the controlled UUID using the actual ClientReporter SHA-256 procedure and each server scope. MachineGuid, fallback IDs, scoped device values and server-scope values remained in memory and are absent from public evidence.',
      'The Java 8 Minecraft 1.16.5 fixtures use the stock authlib OfflineSocialInteractions fallback with an isolated non-listening loopback services endpoint and synthetic access token 0. Account/auth/session hosts and game/library bytes are unchanged; online account authentication is untested.',
      'Forge 1.8.9 graphical acceptance uses enabled=false in the isolated local Forge splash configuration. It is a documented graphics workaround, not a change to Verdict policy or JAR bytes. Forge 1.8.9 to Paper 1.8.8 proves that exact protocol-47 interoperability pair, not a native Forge 1.8.8 adapter.',
      'Bukkit interoperability proves report acceptance by exact device association and continued live queries; it does not claim Bukkit uses or restores the mod-server spectator waiting mode.',
      'No Grim punishment or AntiXray efficacy result is established by this client matrix. Those components have separate, explicitly versioned integration evidence.',
      'Existing modern fixtures include third-party integration mods. Their exact top-level JAR/descriptor inventories are recorded without distributing binaries. Nonfatal upstream REFMAP/minVersion warnings, offline-auth errors and teardown network exceptions remain in raw logs; PASS does not mean an error-free log.',
      'These artifact-bound local runtime results are separate from source-commit CI and any later release-tag CI.'
    ]
    report={'schemaVersion':1,'candidateVersion':'0.2.0-test.1','license':'GPL-3.0-only','status':'PASS_BOUNDED_REAL_CLIENT_MATRIX',
            'passed':True,'allPassed':True,'formalAcceptancePassed':True,'caseCount':14,'matchingModServerCases':12,'bukkitInteroperabilityCases':2,
            'uniqueFirstPartyJarCount':13,'cases':progress['cases'],'attemptHistory':history,'failedAttempts':progress['failedAttempts'],'relatedReports':references,
            'publicEvidence':evidence,'evidenceFileCount':len(evidence),'evidenceBytes':sum(x['bytes'] for x in evidence),
            'privacy':progress['privacy'],'independentAuditorExecutedJava':False,
            'auditorSnapshotScope':'Exact Windows file-auditor source snapshots; reproducing private association checks requires the original private fixture state. These are evidence, not portable installers.',
            'limits':limits}
    exclusive_same(ROOT/'outputs/client-validation-0.2.0-test.1.json',(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
    rows=[]
    for c in report['cases']:
        server=('Paper '+c.get('serverMinecraft',c['minecraft'])) if c['kind']=='bukkit-interoperability' else c['loader']+' '+c['minecraft']
        rows.append('| '+c['loader']+' '+c['minecraft']+' | '+server+' | '+c['loaderVersion']+' | '+c['java']['version']+' | '+str(c['onlineObservationSeconds'])+' | 0 / 0 |')
    doc='''# 0.2.0-test.1 真实客户端验收

本轮 14 组限定组合均通过：12 个新模组分别连接同版专服，另以 Forge 1.12.2 和 Forge 1.8.9 客户端连接装有新 Bukkit 插件的 Paper 1.12.2、Paper 1.8.8。合计覆盖 13 个第一方 JAR；每组均核对实际客户端副本、服务端副本与对应构建记录的 SHA-256，未用旧版 JAR 的历史通过代替新制品。

[完整报告与原始附件白名单](../outputs/client-validation-0.2.0-test.1.json)、[构建记录](../outputs/build-validation-0.2.0-test.1.json)、[成品核心回归](../outputs/artifact-core-validation-0.2.0-test.1.json)。附件只收报告明确列出的原始结果、控制台日志、公开配置、实际执行的测试工具和截图，重复工具按原字节哈希去重。

| 客户端 | 服务端 | 加载器版本 | 实际启动器 Java | 在线观察（秒） | 客户端 / 服务端退出码 |
|---|---|---|---|---:|---|
'''+ '\n'.join(rows)+'''

现代四组的 60 秒从服务端观察到进入游戏开始计算；1.16.5—1.19.4 以首次观察到生存模式恢复后的实时查询计时，1.12.2 / 1.8.9 以报告关联及生存查询确认后至少 65 秒的单调时钟间隔和最后一次新查询为准。各组均超过默认 20 秒报告期限，客户端、服务端均正常退出 0。

每组保留全部 13 项严格默认配置：伴随端和设备报告必需、VM/黑名单 DENY、拒绝触发 BAN，以及原有 IP 配额。测试前后配置 SHA-256 均为 `'''+audit.POLICY_SHA+'''`；新建服务端的 37 条规则与目录的 kind、ID、action、来源逐项一致。独立审阅按 ClientReporter 的真实计算步骤重新验证固定测试账号 UUID 与对应服务端设备值的关联，不只判断状态文件中是否存在任意一条设备记录。

全部截图均独立检查 PNG 签名、每块 CRC、zlib 流、扫描行与解码像素，并逐张通过 `view_image` 查看世界、玩家手臂和生存 HUD。报告记录实际审阅代理与截图哈希；自动 PNG 检查和画面查看是两项分别记录的证据，不等同于性能、长期游玩或全功能测试。

现代服务端夹具还包含既有第三方集成。报告逐组记录客户端、服务端实际 JAR 文件名、SHA-256 与顶层描述符 ID，不把这些二进制放入公开证据。原日志中的上游 REFMAP/minVersion、离线认证及退出阶段网络告警均保留；本轮 PASS 基于准入、在线查询、模式、设备关联、画面和退出码，不表示日志没有 ERROR，也不单独证明第三方行为检测或防透视效果。

Forge 1.8.9 的两组图形测试沿用本机所需的 Forge splash `enabled=false`，仅作用于隔离客户端配置，未修改产品 JAR 或严格策略。该客户端连接 Paper 1.8.8 的结果限定于这个协议 47 组合，不证明原生 Forge 1.8.8 适配。1.12.2 的配置按其实际执行记录保留，不据此套用 1.8.9 的设置。Bukkit 的报告准入由精确设备关联及持续在线查询确认，不声称其曾使用或恢复模组专服的旁观隔离模式。

1.16.5 的 Java 8 图形测试使用原版 authlib 的 OfflineSocialInteractions 回退：只把该进程的 services endpoint 指向隔离且未监听的本机端口，使用合成 token `0`；auth/account/session 官方地址与游戏、库原字节不变。该条件随原始结果保留，不作为正版账号认证已通过的证据。

所有游戏连接为受控本机离线认证夹具；本报告不证明正版账号认证、虚拟机不可伪造、所有作弊客户端识别、Grim 行为处罚或 AntiXray 防透视效果。设备原值、安装标识、服务器 scope、账号状态、世界、库和游戏二进制均未复制进公开证据。实际私有值只在内存中用于关联计算与公开材料泄漏扫描。源码 CI、这里的精确制品运行结果与之后的发布标签 CI 分开记录。
'''
    exclusive_same(ROOT/'docs/client-0.2.0-test.1.md',doc.encode())
    print(json.dumps({'cases':14,'evidenceFiles':len(evidence),'evidenceBytes':report['evidenceBytes'],'reportSha256':digest(ROOT/'outputs/client-validation-0.2.0-test.1.json')}))

if __name__=='__main__': main()
