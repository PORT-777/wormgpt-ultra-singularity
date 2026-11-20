---
name: int-scanners-box-advanced-persistent-threat-detect
description: "Scanner collection: Advanced Persistent Threat Detect (We5ter/Scanners-Box)"
trigger_when: "scanners-box,advanced,persistent,threat,detect,create,collection,commit,convention,authors,legal,disclaimer"
source: Scanners-Box
---
## Advanced Persistent Threat Detect


- https://github.com/Neo23x0/Loki - **Simple IOC and Incident Response Scanner**

> ![](https://img.shields.io/badge/MainLanguage-Python-blue?style=for-the-badge)  ![GitHub last commit](https://img.shields.io/github/last-commit/Neo23x0/Loki?style=for-the-badge) ![GitHub stars](https://img.shields.io/github/stars/Neo23x0/Loki?style=for-the-badge)  ![GitHub](https://img.shields.io/github/license/Neo23x0/Loki?style=for-the-badge)

- https://github.com/Neo23x0/Fenrir - **Simple IOC and Incident Response Scanner**

> ![](https://img.shields.io/badge/MainLanguage-BashShell-blue?style=for-the-badge)  ![GitHub last commit](https://img.shields.io/github/last-commit/Neo23x0/Fenrir?style=for-the-badge) ![GitHub stars](https://img.shields.io/github/stars/Neo23x0/Fenrir?style=for-the-badge)  ![GitHub](https://img.shields.io/github/license/Neo23x0/Fenrir?style=for-the-badge)


***
### Why Create This Collection?

The purpose of this collection is to provide various types of  open-source security scanners that can help companies to be more safer.

### Commit Convention

This project follows [Conventional Commits](https://www.conventionalcommits.org/) for commit messages:

| Type | Description |
|:-----|:------------|
| `feat(scanner): xxx` | Add a new scanner |
| `fix(scanner): xxx` | Update scanner info |
| `remove(scanner): xxx` | Remove a scanner |
| `feat(category): xxx` | Add a new category |
| `remove(category): xxx` | Remove a category |
| `docs(credits): xxx` | Update acknowledgments |
| `chore: xxx` | Other changes |

### Authors

**Wester**(Twitter <a href="http://twitter.com/wester0x01">@Zhiyang Zeng</a>) & **Martin**(Twitter <a href="https://twitter.com/yuyangchow">@Martin Chow</a>)

### Legal Disclaimer

The scanners provided by this project are for research and study purposes only, and you must obey the laws and regulations of your country during use. If you are a Chinese citizen, please ensure you are obedient to *The Cyber Security Law of the People's Republic of China*, and please do not break the article 286 of *the Criminal Law of the People's Republic of China* for the regulation on the crime of destroying computer systems. At last, I would like to point out to you that you must be fully held responsible duty for any consequence that may arise.

### How to contribute?

If you have any questions about this project ,or you have found some valuable scanners, please feel free to tell us :)

### License

The content of this Repository is released under the [<CC BY-NC-ND 4.0>](https://creativecommons.org/licenses/by-nc-nd/4.0/deed.en) license.

### Copyright

It's happy to see that this repository has been widely spreaded in information security community, but I hope everyone could at all times respect knowledge and our efforts, so please specify reproduced from https://github.com/We5ter/Scanners-Box in your articles, and please do not republish this article for profit.

### Acknowledgments

We would like to thanks the following security researchers for their valuable feedbacks amd suggestions.

- **@0c0c0f**
- **@藏形匿影**
- **@Mottoin team**
- **@BlackHole**
- **@CodeColorist**
- **@3xp10it**
- **@re4lity**
- **@s0md3v**
- **@boy-hack**
- **@marsII**
- **@tom0li**
- **@hksanduo**
- **@alexlauerman**
- **@MedivhMT**
- **@TideSec**
- **@0xHJK**
- **@j3ssie**
- **@Luci-d**
- **@cnlnn**
- **@yunxu1**
- **@saeeddhqan**
- **@Sofiane Lounici**
- **Owen Garrettz@deepfence**

### Stargazers

<p align="center">
  <a href="https://github.com/We5ter/Scanners-Box/stargazers">
    <img src="https://img.shields.io/github/stars/We5ter/Scanners-Box?style=for-the-badge&logo=github&color=%23a78bfa&label=⭐%20Star" alt="GitHub Stars">
  </a>
  <br/><br/>
  <img src="https://star-history.dera.page/svg?repos=We5ter/Scanners-Box&type=Date&theme=dark" alt="Star History Chart">
</p>

&copy;<a href="https://github.com/monsterzer0" target="_blank">Monster  Zero Team</a> 2017-2026


---

(cn: 定向APT攻击检测; cn body follows)

- https://github.com/Neo23x0/Loki - **根据公开情报库里的IOC信息检索本地是否存在相同hash的文件或与恶意C2的网络连接**

> ![](https://img.shields.io/badge/主语言-Python-blue?style=for-the-badge)  ![GitHub last commit](https://img.shields.io/github/last-commit/Neo23x0/Loki?style=for-the-badge&label=上次提交)  ![GitHub stars](https://img.shields.io/github/stars/Neo23x0/Loki?style=for-the-badge&label=start数量)  ![GitHub](https://img.shields.io/github/license/Neo23x0/Loki?style=for-the-badge&label=开源协议)

- https://github.com/Neo23x0/Fenrir - **根据公开情报库里的IOC信息检索本地是否存在相同hash、相似文本内容的文件或与恶意C2的网络连接**

> ![](https://img.shields.io/badge/主语言-BashShell-blue?style=for-the-badge)  ![GitHub last commit](https://img.shields.io/github/last-commit/Neo23x0/Fenrir?style=for-the-badge&label=上次提交)  ![GitHub stars](https://img.shields.io/github/stars/Neo23x0/Fenrir?style=for-the-badge&label=start数量)  ![GitHub](https://img.shields.io/github/license/Neo23x0/Fenrir?style=for-the-badge&label=开源协议)


***

### 为什么创建这个合辑？

本合辑的初衷是为了向各类企业安全从业者提供在企业信息安全防护体系建设过程中可以参考的开源安全扫描工具，以期望他们能够利用这些扫描器对业务进行自检，从而保障业务的安全

### 作者

**Wester**(sina weibo <a href="http://weibo.com/zzyme/">@Wester的小号</a>) && **Martin**(sina weibo <a href="http://weibo.com/u/1312149403">@Mart1n_ZHOU</a>)

### 提交规范

本项目遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

| 类型 | 说明 |
|:-----|:-----|
| `feat(scanner): xxx` | 添加新扫描器 |
| `fix(scanner): xxx` | 更新扫描器信息 |
| `remove(scanner): xxx` | 移除扫描器 |
| `feat(category): xxx` | 新增分类 |
| `remove(category): xxx` | 删除分类 |
| `docs(credits): xxx` | 更新致谢榜 |
| `chore: xxx` | 其他变更 |

### 法律声明

本项目所列举的扫描器仅供各位研究学习目的使用，使用过程中也请严格遵守当地法律法规，如果您是中国公民，请严格遵守《中华人民共和国网络安全法》相关规定，也请勿触犯《中华人民共和国刑法》第286条"破坏计算机系统罪"相关条例，否则造成的严重后果与仓库作者无关，特此声明！

### 如何参与？

非常欢迎大家一起来参与建设,如果你有关于此项目的想法、建议或者发现了一些有价值的扫描器，请记得要告诉我们 :)

### 开源协议

本仓库内容在知识共享[《署名-非商业性使用-禁止演绎 4.0 国际协议》](https://creativecommons.org/licenses/by-nc-nd/4.0/deed.zh)条款下发布

### 版权

非常开心能够看到这个仓库在安全社区如此广泛的传播，但我也希望大家能够尊重知识，尊重劳动，因此转载的时候请在您的文章里注明来自https://github.com/We5ter/Scanners-Box ,同时也请不要通过二次发表此文章谋取不正当的利益（如原创投稿）

### 致谢

非常感谢下面这些安全研究员为我们提供的宝贵建议和反馈

- **@0c0c0f**     
- **@藏形匿影**
- **@Mottoin团队**
- **@BlackHole**
- **@CodeColorist**
- **@3xp10it**
- **@re4lity**
- **@s0md3v**
- **@boy-hack**
- **@marsII**
- **@tom0li**
- **@hksanduo**
- **@alexlauerman**
- **@MedivhMT**
- **@TideSec**
- **@0xHJK**
- **@j3ssie**
- **@Luci-d**
- **@cnlnn**
- **@yunxu1**
- **@saeeddhqan**
- **@Sofiane Lounici**
- **Owen Garrett@deepfence**


### Star 轨迹

<p align="center">
  <a href="https://github.com/We5ter/Scanners-Box/stargazers">
    <img src="https://img.shields.io/github/stars/We5ter/Scanners-Box?style=for-the-badge&logo=github&color=%23a78bfa&label=⭐%20Star" alt="GitHub Stars">
  </a>
  <br/><br/>
  <img src="https://star-history.dera.page/svg?repos=We5ter/Scanners-Box&type=Date&theme=dark" alt="Star History Chart">
</p>


&copy;<a href="https://github.com/monsterzer0" target="_blank">Monster Zero Team</a> 2017-2026
