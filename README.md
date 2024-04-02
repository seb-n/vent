# Analyzing social influence on social media

## Crawler installs
- install [node.js](https://nodejs.org/en/download/current)
- install [Appium](http://appium.io/docs/en/latest/quickstart/install/) with npm
- install [uiautomator2 webdriver]([https://nodejs.org/en/download/current](http://appium.io/docs/en/latest/quickstart/uiauto2-driver/))
- pip install [mitmproxy](https://mitmproxy.org/)
- install Android [SDK](https://developer.android.com/studio) - either with android studio (recommended) or through command line 
## emulator setup
- using android studio, [create an emulator](https://developer.android.com/studio/run/emulator#avd) of choice,  I used API 28 for easier mitmproxy setup (with google_apis)
- grab an  [.apk of vent](https://www.apkmirror.com/apk/talklife-ltd/vent-express-yourself-freely/vent-express-yourself-freely-8-17-27-release/)
- install vent on the emulator by drag-and-drop or adb push
- [copy your mitmproxy cert to your emulator](https://docs.mitmproxy.org/stable/howto-install-system-trusted-ca-android/#instructions-for-api-level--28-using--writable-system-1)
