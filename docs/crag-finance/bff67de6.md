---
id: "bff67de6"
title: "NASDAQ - 52 Week Hi/Low | Nasdaq"
source_repo: "facebookresearch/CRAG"
source_path: "crag/finance/7/page_1"
tags: [crag, finance]
confidence: medium
---

window.digitalData = {"pageInstanceID":"production:home:market-activity:nasdaq-52-week-hi-low","page":{"pageInfo":{"author":null,"breadcrumbs":["home","market-activity","nasdaq-52-week-hi-low"],"destinationURL":"https:\/\/www.nasdaq.com\/market-activity\/nasdaq-52-week-hi-low","entryURL":null,"lang":"en","onsiteSearchResults":null,"onsiteSearchTerm":null,"pageID":"home:market-activity:nasdaq-52-week-hi-low","pageName":"nasdaq-52-week-hi-low","pagePathLevel1":"market-activity","pagePathLevel2":"market-activity:nasdaq-52-week-hi-low","pagePathLevel3":null,"pagePathLevel4":null,"pagePathLevel5":null,"publisher":null,"articleTitle":null,"publisherTimestamp":null,"referringURL":null,"sysEnv":null,"timeStamp":1709130692,"refreshDisable":false,"disableVideoAds":false,"customPageName":null,"sponsoredContent":false,"nativeRefreshDisable":[],"platform":"rrp","user\_potential\_nplus":false,"user\_id":0,"user\_subscription\_status":"anonymous"},"category":{"eventType":null,"pageType":"market-activity-landing-page","videoType":null,"storyType":null,"primaryCategory":"market-activity","subCategory":null},"attributes":{"adDisplay":false,"assetClass":null,"businessUnit":null,"campaignParameters":null,"industry":null,"quoteSymbol":null,"region":null,"sponsored":false,"topic":null,"audience":null,"glossaryTerm":null},"additionalAttributes":{"pageType":"market-activity-landing-page","quoteSymbolList":null,"assetClass":null,"primaryTopic":null,"additionalTopics":null,"topicsList":[]}},"user":[{"segment":{"loginStatus":"guest","registrationStatus":"anonymous","cookieOptIn":true,"termsOptIn":false,"offersOptIn":false}}]};

{
"@context": "https://schema.org",
"@graph": [
{
"@type": "Corporation",
"@id": "https://www.nasdaq.com/",
"name": "Nasdaq",
"url": "https://www.nasdaq.com/",
"logo": {
"@type": "ImageObject",
"url": "https://www.nasdaq.com/themes/nsdq/dist/assets/images/logo-half-white.svg"
}
},
{
"@type": "WebPage",
"breadcrumb": {
"@type": "BreadcrumbList",
"itemListElement": [
{
"@type": "ListItem",
"position": 1,
"name": "Home",
"item": "https://www.nasdaq.com/"
},
{
"@type": "ListItem",
"position": 2,
"name": "Market Activity",
"item": "https://www.nasdaq.com/market-activity"
},
{
"@type": "ListItem",
"position": 3,
"item": {
"@id": "https://www.nasdaq.com/market-activity/nasdaq-52-week-hi-low",
"name": "NASDAQ - 52 Week Hi/Low",
"url": "https://www.nasdaq.com/market-activity/nasdaq-52-week-hi-low"
}
}
]
}
},
{
"@type": "WebSite",
"name": "Nasdaq",
"url": "https://www.nasdaq.com/",
"potentialAction": {
"@type": "SearchAction",
"target": "https://www.nasdaq.com/search?q={search\_term\_string}",
"query-input": "required name=search\_term\_string"
}
}
]
}

(function () {
function loadScript(tagSrc,client) {
var scriptTag = document.createElement('script'),
placeTag = document.getElementsByTagName("script")[0];
scriptTag.async = true;
scriptTag.type = "text/javascript";
scriptTag.src = tagSrc;
if (client !== null) {
scriptTag.setAttribute('data-ad-client', client);
}
placeTag.parentNode.insertBefore(scriptTag, placeTag);
}
var smartSrc = "https://ad.wsod.com/site/2caa62b3a3a0755e2cda9deea9070934/0.0.async/";
var autoSrc = "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js";
var client = "ca-pub-1861191755926748";
// Load the Smart Targets script
loadScript(smartSrc,null);
if (window.digitalData.page.category.pageType != 'article-page') {
setTimeout(function () {
if (typeof drupalSettings != "undefined") {
const nplus = drupalSettings.user\_info.user\_nasdaq\_plus;
if (!nplus) {
// Load Google Auto Ads script
loadScript(autoSrc,client);
}
}
}, 2000);
}
})();

// Initialize the prebid variables.
// Initialize the google variables.
var googletag = googletag || {};
googletag.cmd = googletag.cmd || [];
// Add a place to store the slot name variable.
googletag.slots = googletag.slots || {};
// Add a place to store slots that are queued/observed
// These are slots that we already stored but waiting to be fetched
googletag.slotsQueued = googletag.slotsQueued || {};
window.adsList = window.adsList || [];

//Load the APS JavaScript Library
!function(a9,a,p,s,t,A,g){
if(a[a9])return;
function q(c,r){a[a9].\_Q.push([c,r])}
a[a9]={
init:function(){q("i",arguments)},
fetchBids:function(){q("f",arguments)},
setDisplayBids:function(){},
targetingKeys:function(){return[]},\_Q:[]
};
A=p.createElement(s);
A.async=!0;
A.src=t;
g=p.getElementsByTagName(s)[0];
g.parentNode.insertBefore(A,g)
}("apstag",window,document,"script","//c.amazon-adsystem.com/aax2/apstag.js");
//Initialize the Library
apstag.init({
pubID: '3444',
adServer: 'googletag',
bidTimeout: 800,
deals: true
});

window.adsList.push({
id: "js-dfp-tag-5Ts",
name: "/3244/market-activity/ATF\_Leaderboard",
size: [[320, 50], [728, 90], [970, 250]] // Handle fluid size
});
googletag.cmd.push(function() {
// Start by defining breakpoints for this ad.
var mapping = googletag.sizeMapping()
.addSize([0, 0], [320, 50])
.addSize([768, 0], [728, 90])
.addSize([1200, 0], [[728, 90]

...(truncated)