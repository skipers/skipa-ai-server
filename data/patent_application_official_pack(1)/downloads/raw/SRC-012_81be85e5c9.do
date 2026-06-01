<!DOCTYPE html>




<html lang="ko">
<head>
<meta http-equiv="X-UA-Compatible" content="IE=edge" />
<title>KIPRIS 특허정보검색서비스 특허무료검색서비스</title>
<meta name="robots" content="all"/>
<!-- ▼아래는 2019년 메인개편 UI 관련 소스 -->
<link rel="stylesheet" href="/kportal/common/css/layout_new.css" type="text/css">


<meta charset="utf-8" />
<meta name="keywords" content="지식재산처,KIPRIS,키프리스,특허정보검색서비스,특허검색,상표검색,디자인검색,해외상표검색,해외특허검색" />
<meta name="description" content="kipris" />
<meta name="copyright" content="Copyright 2012 kipris. all rights reserved." />
<meta name="viewport" content="width=device-width, initial-scale=0.3, minimum-scale=1, maximum-scale=0.3, user-scalable=yes, target-densitydpi=medium-dpi" />
<link rel="stylesheet" href="/kportal/common/css/basic_new.css"  />
<link rel="stylesheet" href="/kportal/common/css/mediaqueries_new.css"  />
<link rel="stylesheet" href="/kportal/common/css/addSearch.css" />
<!-- ▼아래는 IE9 보다 버전이 낮은 브라우저에서만 이 스크립트를 해석하도록 한 것 -->
<!--[if lt IE 9]><script src="/kportal/common/js/html5.js"></script><![endif]-->
<!--[if lt IE 9]><script src="/kportal/common/js/css3-mediaqueries.js"></script><![endif]-->
<script src="/kportal/common/js/jquery-1.7.1.min.js"></script>
<script src="/kportal/common/js/jquery.cookie.js"></script>
<script src="/kportal/common/js/plani.js"></script>
<script src="/kportal/common/js/ie_print.js"></script>
<script src="/kportal/common/js/bookmark.js"></script>
<script src="/kportal/common/js/counter_checker.jsp"></script>
<script type="text/javascript" src="/kportal/common/js/preview.js"></script>


<link rel="stylesheet" href="http://www.kipris.or.kr/khome/common/css/kipris_event.css"  />
<script type="text/javascript" src="http://www.kipris.or.kr/khome/common/js/kipris_event.js"></script>

<script>
/* ie 버그로 인하여 강제로 탭키 가도록 설정
-------------------------------------------------*/
/*
jQuery(document).ready(function(){
jQuery("#gnavigation").prop("tabindex", "-1");
jQuery("#content").prop("tabindex", "-1");
	});
*/

jQuery(document).ready(function(){
	if(navigator.appName.charAt(0) == "M"){
		jQuery("#gnavigation").prop("tabindex", "-1");
		jQuery("#content").prop("tabindex", "-1");
	}
});

function printPage() {
	window.print() ;
}

function checkValid(V) {

	if (V == void 0 || V == "" || V.length == 0)
		return false ;

	if (V.indexOf(",") != -1 || V.indexOf("@") != -1) {
		throw("[" + V + "]내에 ','나, '@' 문자가 포함되어 있습니다.") ;
	}

	if (! CompareCountChar(V, '(', ')')) {
		throw("검색식의 괄호'(,)'의 개수가 맞지 않습니다.") ;
	}

	if (! CompareCountChar(V, '[', ']')) {
		throw("검색식의 괄호'[,]'의 개수가 맞지 않습니다.") ;
	}

	var quoteCnt = 0 ;
	if (V.indexOf("\"") > -1)
		for (var i = 0 ; i < V.length ; i++) {
			if (V.charAt(i) == '\"') quoteCnt++ ;
		}

	if ((quoteCnt % 2) != 0) {
		throw("쌍따옴표 개수가 일치하지 않습니다.") ;
	}

	return true ;

}

function checkValidation(V) {

	V = DelSpecialChar(V) ;

	if (V.indexOf('!') > -1) {
		if (V.indexOf(' ') == -1 && V.indexOf('*') == -1) {
			throw( "<NOT> 연산자 '!'은 <AND> 연산자 '*' 와 함께 쓰셔야합니다.") ;
		}
	}

	return checkSpecialChar(V) ;

}

function checkSpecialChar(V) {

	var str = V ;
	str = str.replace(/[\*\+\?\)\(\!]/g, ' ') ;

	var tempvalue = str ;
	var specialchar = '#$%^&|\\{}[]\';,.~=<>()+*?@!`' ;

	tempvalue = tempvalue.replace(/ /g, '') ;
	for (var i = 0 ; i < specialchar.length ; i++) {
		for (var k = 0 ; k < str.length ; k++) {
			if (str.charAt(k) == specialchar.charAt(i)) {
				throw("특수문자는 사용할수 없습니다 [ " + specialchar.charAt(i) + " ]") ;
			}
		}
	}
	return true ;
}

function checkKoreanOnly(V) {

	var c ;
	if (V == null) return false ;

	for (var i = 0 ; i < V.length ; i++) {
		c = V.charCodeAt(i) ;
//( 0xAC00 <= c && c <= 0xD7A3 ) 초중종성이 모인 한글자
//( 0x3131 <= c && c <= 0x318E ) 자음 모음

		if (0x3131 <= c && c <= 0x318E) {
//obj.charAt(i)
			throw("단어의 철자가 정확한지 확인해 주십시오.") ;
		}
	}

	return true ;
}

function isKeywordValidation(S) {

	if (S == void 0 || S == "" || S.length == 0) {
		throw("검색어를 입력해 주십시요.") ;
	}
	S = S.replace(/\r\n/g, "") ;
	if (checkValid(S) && checkValidation(S) && checkKoreanOnly(S)) {
		return (DelSpecialChar(S) != "") ;
	}

	return true ;
}

</script>
<style type="text/css">
#searchError { height : 700px; }

#patentResultLoadingBoard { position : absolute; background : #FFF; z-index : 2; }
#patentResultLoading { position : absolute; display: none; z-index : 3; }

#designResultLoadingBoard { position : absolute; background : #FFF; z-index : 2; }
#designResultLoading { position : absolute; display: none; z-index : 3; }

#trademarkResultLoadingBoard { position : absolute; background : #FFF; z-index : 2; }
#trademarkResultLoading { position : absolute; display: none; z-index : 3; }

#frnUSResultLoadingBoard { position : absolute; background : #FFF; z-index : 2; }
#frnUSResultLoading { position : absolute; display: none; z-index : 3; }

#frnEUResultLoadingBoard { position : absolute; background : #FFF; z-index : 2; }
#frnEUResultLoading { position : absolute; display: none; z-index : 3; }

#frnPCTResultLoadingBoard { position : absolute; background : #FFF; z-index : 2; }
#frnPCTResultLoading { position : absolute; display: none; z-index : 3; }

#frnJPResultLoadingBoard { position : absolute; background : #FFF; z-index : 2; }
#frnJPResultLoading { position : absolute; display: none; z-index : 3; }

#frnCNResultLoadingBoard { position : absolute; background : #FFF; z-index : 2; }
#frnCNResultLoading { position : absolute; display: none; z-index : 3; }

#frnENResultLoadingBoard { position : absolute; background : #FFF; z-index : 2; }
#frnENResultLoading { position : absolute; display: none; z-index : 3; }

#frnDEResultLoadingBoard { position : absolute; background : #FFF; z-index : 2; }
#frnDEResultLoading { position : absolute; display: none; z-index : 3; }

#frnFRResultLoadingBoard { position : absolute; background : #FFF; z-index : 2; }
#frnFRResultLoading { position : absolute; display: none; z-index : 3; }

#frnAUResultLoadingBoard { position : absolute; background : #FFF; z-index : 2; }
#frnAUResultLoading { position : absolute; display: none; z-index : 3; }

#frnCAResultLoadingBoard { position : absolute; background : #FFF; z-index : 2; }
#frnCAResultLoading { position : absolute; display: none; z-index : 3; }

#frnRUResultLoadingBoard { position : absolute; background : #FFF; z-index : 2; }
#frnRUResultLoading { position : absolute; display: none; z-index : 3; }

#frnTWResultLoadingBoard { position : absolute; background : #FFF; z-index : 2; }
#frnTWResultLoading { position : absolute; display: none; z-index : 3; }

#ndslArticleResultLoadingBoard { position : absolute; background : #FFF; z-index : 2; }
#ndslArticleResultLoading { position : absolute; display: none; z-index : 3; }

#ipnaviPrcdnResultLoadingBoard { position : absolute; background : #FFF; z-index : 2; }
#ipnaviPrcdnResultLoading { position : absolute; display: none; z-index : 3; }

#ipnaviConflictResultLoadingBoard { position : absolute; background : #FFF; z-index : 2; }
#ipnaviConflictResultLoading { position : absolute; display: none; z-index : 3; }

/* TODO
#ipnaviGuidebookResultLoadingBoard { position : absolute; background : #FFF; z-index : 2; }
#ipnaviGuidebookResultLoading { position : absolute; display: none; z-index : 3; }
*/

.search_blank { height : 80px; }

.total_more { display: none; }


#searchError,
#resultPatent,
#resultDesign,
#resultTrademark,
#resultNdslArticle,
#resultFrnUS,
#resultFrnEU,
#resultFrnPCT,
#resultFrnJP,
#resultFrnCN,
#resultFrnEN,
#resultFrnDE,
#resultFrnFR,
#resultFrnAU,
#resultFrnCA,
#resultFrnRU,
#resultFrnTW,
#resultFrnTW,
#resultIpnaviPrcdn,
#resultIpnaviConflict {display: none; }
/*
#resultIpnaviGuidebook {display: none; }
*/

</style>
</head>

<body>


<dl id="accessibility">
				<dt>컨텐츠 바로가기 영역</dt>
 <dd><a onclick="$('div.search_section_head button:first').focus();" tabindex="0">본문으로 바로가기</a></dd>
 <dd><a onclick="$('#gnb > li:first > a').focus();" tabindex="0">주메뉴로 바로가기</a></dd>
 <dd><a onclick="$('li.menu01 > a').focus();" tabindex="0">사이드메뉴로 바로가기</a></dd>
</dl>
<div id="wrapper">
	<header id="header">
		





<div id="header_bar">
	<div class="grab">
		<div class="topLink">
			<a href="https://www.kipris.or.kr/enghome/main.jsp" target="_blank" title="KIPRIS 영문사이트 새창으로 열림" class="link blue">ENGLISH</a>
		</div>
		<ul class="topMenu">
		
			<li><a tabindex="0" style="cursor: pointer;" onclick="newPopupWindow('/kportal/loginRedirect.jsp', 'login', 700, 400, 'C', 'T');" title="새창으로 열림">로그인</a></li>
			<li><a href="http://login.kipris.or.kr/member/kr/join/memberAction.do?act=joinSelectType">회원가입</a></li>
		
			<li><a href="http://www.kipris.or.kr/khome/sitemap/sitemap.jsp">사이트맵</a></li>
		</ul>
	</div>
</div>

<!--### 로고와 네비게이션 ###-->
<div class="gnbWrap">
	<div class="grab">
		<h1 class="logo"><a href="http://www.kipris.or.kr/khome/main.jsp"><img src="/kportal/images/common/logo01_2022_V.2.png" alt="특허정보검색서비스 키프리스 메인화면으로 이동"></a></h1>
		<h2 class="sr-only">주메뉴 영역</h2>
		
		<nav id="cbp-hrmenu" class="cbp-hrmenu">
			<ul id="gnb" class="depth1">
				<li class="cbp-hropen depth1-1">
					<a tabindex="0" style="cursor: pointer;">지식재산권 검색<i class="arrow"><img src="/kportal/images/main_new/gnb_activeArr.png" alt=""></i></a>
					<div class="cbp-hrsub">
						<ul class="cbp-hrsub-inner depth2"> 
							<li><a href="https://www.kipris.or.kr/kpat/searchLogina.do?next=MainSearch">특허·실용신안</a></li>
							<li><a href="https://www.kipris.or.kr/kdtj/searchLogina.do?method=loginDG">디자인</a></li>
							<li><a href="https://www.kipris.or.kr/kdtj/searchLogina.do?method=loginTM">상표</a></li>
							<li><a href="https://www.kipris.or.kr/kdtj/searchLogina.do?method=loginJM">심판</a></li>
							<li><a href="https://www.kipris.or.kr/kpa/search/search_kpa.do" target="_blank" title="한국특허영문초록 새창으로 열림">KPA</a></li>
							<li><a href="https://www.kipris.or.kr/abpat/searchLogina.do?next=MainSearch">해외특허</a></li>
							<li><a href="https://www.kipris.or.kr/abtm/search/resultList.jsp">해외상표</a></li>
							<li><a href="https://www.kipris.or.kr/abdg/searchLogina.do?next=MainSearch">해외디자인</a></li> 
							<li><a href="https://www.kipris.or.kr/kpat/searchLogina.do?next=CyberSearch">인터넷기술공지</a></li>
							<li><a href="https://www.kipris.or.kr/kpat/searchLogina.do?next=ContestSearch">아이디어공모전</a></li>
							<li><a href="http://www.kipris.or.kr/kdc/searchLogina.do?next=MainSearch">문장검색</a></li>
						</ul>
						<!-- /cbp-hrsub-inner -->
					</div>
					<!-- /cbp-hrsub -->
				</li>
				<li class="depth1-2">
					<span><a href="http://www.kipris.or.kr/khome/today/today.jsp" class="tm">투데이 키프리스</a></span>
				</li>
				<li class="depth1-3">
					<a tabindex="0" style="cursor: pointer;">키프리스 소개<i class="arrow"><img src="/kportal/images/main_new/gnb_activeArr.png" alt=""></i></a>
					<div class="cbp-hrsub">
						<ul class="cbp-hrsub-inner depth2"> 
							<li><a href="http://www.kipris.or.kr/khome/pr/pr.jsp" class="tm">홍보</a></li>
							<li><a href="http://www.kipris.or.kr/khome/guideMaina.do" class="tm">가이드</a></li>
							<li><a href="http://www.kipris.or.kr/khome/kipris/kipris.jsp" class="tm">개요</a></li>
						</ul>
						<!-- /cbp-hrsub-inner -->
					</div>
					<!-- /cbp-hrsub -->
				</li>
			</ul>
		</nav>
		
		<script>
			var cbpHorizontalMenu=(function(){
				var $listItems = $("#cbp-hrmenu > ul > li"),
				$menuItems = $listItems.children("a"),
				current = 0;
				
				function init(){
					$menuItems.on("click", open);
					$listItems.on("click", function(event){
						event.stopPropagation()
					})
				}
				
				function open(event){
					if(current !== -1){
						$listItems.eq(current).removeClass("cbp-hropen")
					}
					
					var $item = $(event.currentTarget).parent("li"),
					idx = $item.index();
					$item.addClass("cbp-hropen");
					current = idx;
					
					return false;
				}
				
				return{ init : init };
			})();
			
			$(function() {
				cbpHorizontalMenu.init();
			});
		</script>
	</div>
</div>

<script>
	$(document).ready(function(){
		$('.tm').bind("click", saveStat);
		
		// 네비게이션 대메뉴(지식재산권 검색, 투데이키프리스, 키프리스소개) 포커스 시, 시각화 추가 및 엔터키 트리거 추가
		$("#gnb").children("li").not(":eq(1)").children("a").on("keyup",
				function(e){
					if(e.keyCode == 13) $(this).trigger("click");
				});
		$("#accessibility a").on("keypress", function(e)
				  {
				   if(e.keyCode == 13) $(this).trigger("click");
				  });
	});
	
	function goMemberLogin() {
		newPopupWindow("/kportal/loginRedirect.jsp", "wLoginPop", 700, 400, "C", "T", "location=yes, toolbar=no, status=yes, resizable=no") ;
	}
	
	//상단 네비게이션 이용통계 추가 by 2014.09.15
	function saveStat(){
	    var href = $(this).attr('href');
	
	    if(href.indexOf('today.jsp') > -1){ //today
	        SaveOpsvcData('KR', 'KPOR', 'HEAD', 'TODAY');
	    } else if(href.indexOf('pr.jsp') > -1){ //PR
	        SaveOpsvcData('KR', 'KPOR', 'HEAD', 'PR');
	    } else if(href.indexOf('guideMaina.do') > -1){ //GUIDE
	        SaveOpsvcData('KR', 'KPOR', 'HEAD', 'GUIDE');
	    } else if(href.indexOf('kipris.jsp') > -1){ //KIPRIS
	        SaveOpsvcData('KR', 'KPOR' , 'HEAD', 'KIP'); 
	    }
	}
	
	/**
	 * 부가서비스 통계 저장
	 * 2013.01.31 bhhan
	 */
	function SaveOpsvcData(lang_tpcd, svc_tpcd, loctn_tpcd, itm_tpcd) {
		var jsonpost = new Object();
		
		jsonpost.lang_tpcd = lang_tpcd;
		jsonpost.svc_tpcd = svc_tpcd;
		jsonpost.loctn_tpcd = loctn_tpcd;
		jsonpost.itm_tpcd = itm_tpcd;
		
		$.ajax({
			url : "/kportal/stata.do",
			type : 'post',
			data : jsonpost,
			async : true,
			cache : true,
			datatype: 'html',
			success : function(data)
			{
				//alert(data);
			},
			error : function()
			{
				hideLoadingBar();
			}
		});
	}
</script>
		

<!-- 헤더영역 -->

<style type="text/css">
#searchKeywordHistoryListBoard { width : 9990px ; }
#historyControllerBoard { display : none ; }
.hidden { display : none ; }
</style>
<script type="text/javascript">

var textPosition = "" ;

</script>
<div id="total_search">
<form name="totalSearchFrm" id="totalSearchFrm" method="post" action="/kportal/search/total_search.do" >
<input type="hidden" id="forwardSearchType" name="searchType" value="" />
<input type="hidden" id="forwardQueryText" name="queryText" value="" />
<input type="hidden" id="forwardExpression" name="expression" value="" />
<input type="hidden" id="forwardSortField" name="sortField" value="" />
<input type="hidden" id="forwardSortState" name="sortState" value="" />
<input type="hidden" id="forwardSortField1" name="sortField1" value="" />
<input type="hidden" id="forwardSortState1" name="sortState1" value="" />
<input type="hidden" id="merchandiseString" name="merchandiseString" value="" />
<input type="hidden" id="measureString" name="measureString" value="" />
<input type="hidden" id="patternString" name="patternString" value="" />
<input type="hidden" id="forwardCollectionValues" name="collectionValues" value="" />
<input type="hidden" id="forwardConfig" name="config" value="" />
<input type="hidden" id="forwardUserId" name="userId" value="" />
<input type="hidden" id="forwardConfigChange" name="configChange" value="" />
<input type="hidden" id="forwardSelectedLang" name="selectedLang" value="" />
<input type="hidden" id="forwardLang" name="lang" value="" />
<input type="hidden" id="pageNum" name="pageNum" value="1" />
<input type="hidden" id="searchExpression" name="searchExpression" value="" />
<input type="hidden" id="searchInTrans" name="searchInTrans" value="" />

<input type="hidden" id="beforeExpression" name="beforeExpression" value="" />
		<fieldset>
			<legend>검색</legend>
	<div class="lside_menu">
<!-- 		<a id="btnCheckExtend" href="javascript:;"> -->
			<span id="searchInTransCkBtn" style="cursor: pointer;" class="search_extend">
				<input type="checkbox" id="searchInTransCk" name="searchInTransCk" value="" />
				<label for="searchInTransCk">검색어확장</label>
			</span>
<!-- 		</a> -->
	</div>
	<div id="searchAreaTop">
		<div id="divSearchItems" class="hsearch">
			<div id="selectSearchTypeBtn" class="search_selectBox" style="cursor:pointer;">
				<a href="javascript:;"><span id="spanSelected01Img" class="hidden"><img src="/kportal/images/common/txt_keyword01.gif" alt="통합검색"/></span></a>
				<span id="spanSelected02Img" class="hidden"><img src="/kportal/images/common/txt_keyword02.gif" alt="특허&middot;실용신안"/></span>
				<span id="spanSelected03Img" class="hidden"><img src="/kportal/images/common/txt_keyword03.gif" alt="디자인"/></span>
				<span id="spanSelected04Img" class="hidden"><img src="/kportal/images/common/txt_keyword04.gif" alt="상표"/></span>
				<span id="spanSelected05Img" class="hidden"><img src="/kportal/images/common/txt_keyword05.gif" alt="심판"/></span>
				<span id="spanSelected06Img" class="hidden"><img src="/kportal/images/common/txt_keyword06.gif" alt="KPA"/></span>
				<span id="spanSelected07Img" class="hidden"><img src="/kportal/images/common/txt_keyword07.gif" alt="해외특허"/></span>
				<span id="spanSelected08Img" class="hidden"><img src="/kportal/images/common/txt_keyword08.gif" alt="해외상표"/></span>
                                <span id="spanSelected10Img" class="hidden"><img src="/kportal/images/common/txt_keyword10.gif" alt="해외디자인"/></span>
				<ul id="ulSelPatArea" >
					<li><a id="btnSelPat01" style="cursor:pointer;" href="javascript:;"><img src="/kportal/images/common/txt_keyword01.gif" alt="전체" /></a></li>
					<li><a id="btnSelPat02" style="cursor:pointer;" href="javascript:;"><img src="/kportal/images/common/txt_keyword02.gif" alt="특허&middot;실용신안" /></a></li>
					<li><a id="btnSelPat03" style="cursor:pointer;" href="javascript:;"><img src="/kportal/images/common/txt_keyword03.gif" alt="디자인" /></a></li>
					<li><a id="btnSelPat04" style="cursor:pointer;" href="javascript:;"><img src="/kportal/images/common/txt_keyword04.gif" alt="상표" /></a></li>
					<li><a id="btnSelPat05" style="cursor:pointer;" href="javascript:;"><img src="/kportal/images/common/txt_keyword05.gif" alt="심판" /></a></li>
					<li><a id="btnSelPat06" style="cursor:pointer;" href="javascript:;"><img src="/kportal/images/common/txt_keyword06.gif" alt="KPA" /></a></li>
					<li><a id="btnSelPat07" style="cursor:pointer;" href="javascript:;"><img src="/kportal/images/common/txt_keyword07.gif" alt="해외특허" /></a></li>
					<li><a id="btnSelPat08" style="cursor:pointer;" href="javascript:;"><img src="/kportal/images/common/txt_keyword08.gif" alt="해외상표" /></a></li>
                                        <li><a id="btnSelPat10" style="cursor:pointer;" href="javascript:;"><img src="/kportal/images/common/txt_keyword10.gif" alt="해외디자인" /></a></li>
				</ul>
			</div>
                        <!--label for="searchKeyword" id="ol_queryTextlabel">ex)1020000038308, 핸드폰, G08G, 출원인명...</label-->
			<input type="text" id="searchKeyword" name="searchKeyword" value="" class="keyword" title="검색어입력" style="ime-mode:active;"/>
			<div class="keyword_txtopen">
				<button type="button" id="searchQueryInputBtn" class="btn_keyword_open">펼치기</button>
				<!-- <button id="btnKeywordareaClose" type="button" class="btn_keyword_close">닫기</button>	-->
				<div id="searchQueryInputBox" class="keyword_area">
					<label for="searchQueryInput">검색어확장</label><textarea name="searchQueryInput" id="searchQueryInput" cols="78" rows="5" style="ime-mode:active;"></textarea>
				</div>
			</div>
			<span class="input_btn"><button title="검색" type="submit" id="initSearchResultPageFrmNewBookMark"><img src="/kportal/images/common/btn_search.gif" alt="검색" /></button></span>
			<span class="reSearch"><input type="checkbox" id="innerSearchCk" name="searchInResult" value="Y"/> <label for="innerSearchCk"><img src="/kportal/images/common/txt_reSearch.gif" alt="결과 내 재검색"/></label></span>
		</div>
		<div class="search_keyword">
			<h2><img src="/kportal/images/common/title_newSearch.gif" alt="검색히스토리" /></h2>
			<div id="searchKeywordHistoryListContainer" class="keyword_txt"><div id="searchKeywordHistoryListBoard"></div></div>
			<div id="historyControllerBoard" class="page"><span class="page_prew"><button id="btnHistoryPrev" type="button">이전 검색어</button></span><span class="page_next"><button id="btnHistoryNext" type="button">다음 검색어</button></span></div>
		</div>
	</div>
		</fieldset>
	</form>
</div>
<script type="text/javascript">
/*
jQuery("#initSearchResultPageFrmNewBookMark").click(
	function(evt) {
            //By J.H.S 페이지당 (30,60,90) GO 버튼 클릭시 북마크 선택된 값을 초기화 하기위해 추가. 
            jQuery("#NWBOOKMARK", "#searchResultPageFrm").finval("");
	}
) ;
*/

jQuery("#searchKeyword").focus(
	function(evt) {
		textPosition = "INPUT" ;
	}
) ;

jQuery("#searchQueryInput").focus(
	function(evt) {
		textPosition = "TEXT" ;
	}
) ;

jQuery("#searchInTransCkBtn").click(
	function(evt) {
		if (jQuery("#searchInTransCk").prop("checked")) {
			jQuery("#searchInTransCk").prop("checked", false) ;
			jQuery(this).removeClass("extend_on") ;
		} else {
			jQuery("#searchInTransCk").prop("checked", true) ;
			jQuery(this).addClass("extend_on") ;
		}
	}
) ;

jQuery("#innerSearchCk").click(
	function(evt) {
		
                //By J.H.S 20140813 검색하게 되면 검색어를 beforeExpression에 저장함
                //국문홈페이지 검색 후 결과내 재검색 할때 처리하기 위해 
                jQuery("#beforeExpression").val(jQuery("#searchExpression").val()) ;
                
                if (jQuery("#beforeExpression").val() == "") {
			evt.preventDefault() ;
			alert("검색 하신 후 사용하실 수 있습니다.") ;
		} else {
			jQuery("#searchKeyword").val("") ;
			jQuery("#searchKeyword").focus() ;
		}
	}
) ;

var isSelectSearchListVisible = false ;
jQuery("#selectSearchTypeBtn").click(
	function(evt) {
		if (isSelectSearchListVisible) {
			jQuery("#ulSelPatArea").hide() ;
		} else {
			jQuery("#ulSelPatArea").show() ;
		}
		isSelectSearchListVisible = !isSelectSearchListVisible ;
	}
) ;
function hideSearchType(TN) {
	jQuery("#spanSelected01Img").hide() ;
	jQuery("#spanSelected02Img").hide() ;
	jQuery("#spanSelected03Img").hide() ;
	jQuery("#spanSelected04Img").hide() ;
	jQuery("#spanSelected05Img").hide() ;
	jQuery("#spanSelected06Img").hide() ;
	jQuery("#spanSelected07Img").hide() ;
	jQuery("#spanSelected08Img").hide() ;
        jQuery("#spanSelected10Img").hide() ;
       // jQuery("#spanSelected11Img").hide() ;
	jQuery("#spanSelected" + TN + "Img").show() ;
}
jQuery("#btnSelPat01").click(function() {
	jQuery("#forwardSearchType").val("total") ; hideSearchType("01") ;
}) ;
jQuery("#btnSelPat02").click(function() {
	jQuery("#forwardSearchType").val("patent") ; hideSearchType("02") ;
}) ;
jQuery("#btnSelPat03").click(function() {
	jQuery("#forwardSearchType").val("design") ; hideSearchType("03") ;
}) ;
jQuery("#btnSelPat04").click(function() {
	jQuery("#forwardSearchType").val("trademark") ; hideSearchType("04") ;
}) ;
jQuery("#btnSelPat05").click(function() {
	jQuery("#forwardSearchType").val("judgement") ; hideSearchType("05") ;
}) ;
jQuery("#btnSelPat06").click(function() {
	jQuery("#forwardSearchType").val("kpa") ; hideSearchType("06") ;
}) ;
jQuery("#btnSelPat07").click(function() {
	jQuery("#forwardSearchType").val("abpat") ; hideSearchType("07") ;
}) ;
jQuery("#btnSelPat08").click(function() {
	jQuery("#forwardSearchType").val("abtm") ; hideSearchType("08") ;
}) ;
jQuery("#btnSelPat10").click(function() {
	jQuery("#forwardSearchType").val("abdg") ; hideSearchType("10") ;
}) ;
/*
jQuery("#btnSelPat11").click(function() {
	jQuery("#forwardSearchType").val("cntst") ; hideSearchType("11") ;
}) ;
*/
jQuery("#forwardSearchType").val("total") ; hideSearchType("01") ;

function setSearchKeywordHistory(V) {
	jQuery("#searchQueryInput").val(V) ;
	jQuery("#searchKeyword").focus() ;
	jQuery("#searchKeyword").val(V) ;
}

jQuery("#btnHistoryPrev").click(
		function(evt) {
			var mV = 0 ;
			var tV = 0 ;
			var isLimitY = true ;
                        
                        //상단 검색 placeholder hidden By J.H.S 20131022
                        //$('#ol_queryTextlabel').css('visibility','hidden');
                        
			jQuery("#searchKeywordHistoryListBoard").children().each(
				function() {
					tV += jQuery(this).outerWidth(true) ;
					if (isLimitY)
						mV += jQuery(this).outerWidth(true) ;
					if (mV >= jQuery("#searchKeywordHistoryListContainer").prop("scrollLeft")) {
						mV -= jQuery(this).outerWidth(true) ;
						isLimitY = false ;
					}
				}
			) ;
			if (mV < 0) mV = 0 ;
			if (jQuery("#searchKeywordHistoryListContainer").prop("scrollLeft") > 0) {
				jQuery("#searchKeywordHistoryListContainer").animate({"scrollLeft":mV}, 200) ;
			}
		}
) ;

jQuery("#btnHistoryNext").click(
		function(evt) {
			var mV = 0 ;
			var tV = 0 ;
                        
                        //상단 검색 placeholder hidden By J.H.S 20131022
                        //$('#ol_queryTextlabel').css('visibility','hidden');
                        
			jQuery("#searchKeywordHistoryListBoard").children().each(
				function() {
					tV += jQuery(this).outerWidth(true) ;
					if (mV <= jQuery("#searchKeywordHistoryListContainer").prop("scrollLeft")) {
						mV += jQuery(this).outerWidth(true) ;
					}
				}
			) ;
			if (jQuery("#searchKeywordHistoryListContainer").prop("scrollLeft") + jQuery("#searchKeywordHistoryListContainer").prop("clientWidth") < tV) {
				jQuery("#searchKeywordHistoryListContainer").animate({"scrollLeft":mV}, 200) ;
			}
		}
) ;

function regChk(vTok){
	 var result = vTok;
	 //var regExp = /^(?:[0-9]{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12][0-9]|3[01]))-[1-4][0-9]{6}$/;
	 var regExp = /^(?:[0-9]{6})-(?:[0-9]{7})$/;
	 
	 if(vTok.match(regExp) != null){
		 result = "******-*******";
	 }
	 
	 return result;
}

function cutStr(vTok){
	 var result = vTok;
	 
	 if(vTok.length > 15){
		 result = vTok.substring(0, 15);
		 result += "...";
	 }
	 
	 return result;
}

function setSearchKeywordHistoryBoard() {
	jQuery("#searchKeywordHistoryListBoard").empty() ;
	jQuery("#searchKeywordHistoryListContainer").prop("scrollLeft", "0") ;
	jQuery("#historyControllerBoard").hide() ;
	var historyWords = jQuery.cookie(KIPRIS_TOTAL_HISTORY_KEY) ;
	if (historyWords == void 0 || historyWords == "") {
	} else {
		var historyWord = historyWords.split("|") ;
		for (var i = 0 ; i < historyWord.length ; i++) {
			jQuery("#searchKeywordHistoryListBoard").append("<span id='spanHistory" + i + "'>");
			var regChkWord = regChk(decodeURIComponent(historyWord[i]));
			var cutWord = cutStr(regChkWord);
			var newTagStr = "<a id='btnHistory" + i + "' title='" + regChkWord + "' href='#' onclick='return false;'>" + cutWord + "</a>";
			var newTag = jQuery(newTagStr) ;
			jQuery("#spanHistory" + i).append(newTag) ;
			var delTagStr = "<a id='btnHistoryDel" + i + "' title='" + regChkWord + "' href='#' onclick='return false;'><img src=\"/kportal/images/service/btn_del.png\" alt=\"검색히스토리 선택삭제\" /></a>";
			var delTag = jQuery(delTagStr) ;
			jQuery("#spanHistory" + i).append(delTag) ;
			jQuery(newTag).click(
					function(evt) {
						setSearchKeywordHistory(this.title) ;
					}
				) ;
			jQuery(delTag).click(
					function(evt) {
						var delNum = this.id;
						delNum = delNum.replace("btnHistoryDel", "");
						
						if(historyWord.length == 1){
							jQuery.removeCookie(KIPRIS_TOTAL_HISTORY_KEY, getCookieOption());
						} else {
							var saveHistoryWord = "";
							for (var i = 0 ; i < historyWord.length ; i++) {
								if(delNum != i){
									if(saveHistoryWord == ""){
										saveHistoryWord = historyWord[i];
									} else {
										saveHistoryWord += "|" + historyWord[i];
									}
								}
							}
							
							jQuery.cookie(KIPRIS_TOTAL_HISTORY_KEY, saveHistoryWord, getCookieOption());
						}
						setSearchKeywordHistoryBoard() ;
					}
				) ;
		}

		var hCW = 0 ;
		jQuery("#searchKeywordHistoryListBoard").children().each(
				function() {
					hCW += jQuery(this).outerWidth(true) ;
				}
			) ;
		if (jQuery("#searchKeywordHistoryListContainer").prop("clientWidth") < hCW) {
			jQuery("#historyControllerBoard").show() ;
		}

	}
}

setSearchKeywordHistoryBoard() ;

</script>
<form name="searchResultFrm" id="searchResultFrm" method="post">
<input type="hidden" id="resultQuery" name="queryText" value="" />
<input type="hidden" id="resultExpression" name="expression" value="" />
<input type="hidden" id="resultExtends" name="extends" value="" />
<input type="hidden" id="resultSearchInTransKorToEng" name="searchInTransKorToEng" value="" />
<input type="hidden" id="resultSearchInTransEngToKor" name="searchInTransEngToKor" value="" />
</form>

<!-- 분리 예정 -->
<form name="searchResultNdsl" id="searchResultNdsl" method="post">
<input type="hidden" id="ndslQueryText" name="queryText" value="" />
<input type="hidden" id="ndslQuery" name="query" value="" />
<input type="hidden" id="ndslExpression" name="expression" value="" />
<input type="hidden" id="ndslDisplayCount" name="displayCount" value=""/>
<input type="hidden" id="ndslStartPosition" name="startPosition" value=""/>
<input type="hidden" id="ndslCategory" name="category" value=""/>
<input type="hidden" id="strstat" name="strstat" value=""/>
</form>
<script type="text/javascript">

var isSearchExtends = false ;

var isVisibleQueryBox = false ;

jQuery("#searchQueryInputBtn").click(
		function() {
			if (isVisibleQueryBox) {
				jQuery("#searchQueryInputBox").hide() ;
				jQuery(this).removeClass().addClass("btn_keyword_open") ;
				jQuery("#searchKeyword").val(jQuery("#searchQueryInput").val()) ;
				textPosition = "INPUT" ;
				jQuery("#searchKeyword").focus() ;
			} else {
				jQuery("#searchQueryInputBox").show() ;
				jQuery(this).removeClass().addClass("btn_keyword_close") ;
				jQuery("#searchQueryInput").val(jQuery("#searchKeyword").val()) ;
				textPosition = "TEXT" ;
				jQuery("#searchQueryInput").focus() ;
			}
			isVisibleQueryBox = !isVisibleQueryBox ;
		}
	) ;

//By J.H.S 20140807 텍스트박스 입력후 EnterKey 눌렀을때 작동
jQuery("#searchQueryInput").keydown(
		function(evt) {
			if (evt.keyCode == 13) {
				if (isVisibleQueryBox) {  //텍스트박스 열기하고 검색식 입력후 Enter 누를때
                                        jQuery("#searchQueryInputBox").hide() ; //텍스트박스 닫기
                                        jQuery("#searchQueryInputBtn").removeClass().addClass("btn_keyword_open") ; //텍스트박스 spread 이미지로 바꾸기
                                        jQuery("#searchKeyword").val(jQuery("#searchQueryInput").val()) ; //텍스트박스 검색어를 텍스트에 넣기
                                        textPosition = "TEXT" ;                  //textPosition TEXT 상태로 바꾸기
                                        jQuery("#searchKeyword").focus() ;       //텍스트에 포커스 맞추기
                                        isVisibleQueryBox = !isVisibleQueryBox ; //isVisibleQueryBox 상태값 false 바꾸기
                                        
                                        evt.preventDefault() ;
                                        jQuery("#totalSearchFrm").submit() ;
                                }
			}
		}
	) ;

function goTotalSearching() {
	try {
         jQuery("#searchResultSearchPage").val(1);
         
         jQuery("#BOOKMARK", jQuery("#searchResultPageFrm")).val("");         
         jQuery("#NWBOOKMARK", jQuery("#searchResultPageFrm")).val(""); 
         jQuery("#FROM", jQuery("#searchResultPageFrm")).val(""); // 실시간, 전체검색 시 북마크 초기화
         
        //By J.H.S 20131022 상단검색 placeholder 숨김
        //$('#ol_queryTextlabel').css('visibility','hidden');
                
		jQuery("#searchError").hide() ;

		var searchKeyword = "" ;
                
                /* By J.H.S 20130813 통합검색 검색시 출원번호, 등록번호 - 형식으로 입력시 "" 치환하여 검색식 입력하도록 개선함. */                
                //searchKeyword = trim(jQuery("#searchQueryInput").val()) ;  //[펼치기]에서 입력값 가져오는것
                searchKeyword = trim(jQuery("#searchKeyword").val()) ;       //text 입력에서 입력값 가져오는것
                                
                //입력된 숫자가 등록번호형식일 경우 "10-0000123" 대쉬 제거 by lhy 2013.03.19
                var regExpRegNum1 = /^\d{2}-\d{7}$/;    
                if(regExpRegNum1.test(searchKeyword)){
                    searchKeyword = searchKeyword.replace("-","");
                    jQuery("#searchKeyword").val(searchKeyword);     //등록번호 형식일 경우 - -> "" 치환하여 text에 변환
                    jQuery("#searchQueryInput").val(searchKeyword);  //등록번호 형식일 경우 - -> "" 치환하여 [펼치기]에 변환 || 이 부분을 세팅 해줘야 [펼치기]하고서 출원번호, 등록번호 치환이 됨.
                }
                //입력된 숫자가 등록번호형식일 경우 "10-0000123-0000" 대쉬 제거 by lhy 2013.03.19
                var regExpRegNum2 = /^\d{2}-\d{7}-\d{4}$/;    
                if(regExpRegNum2.test(searchKeyword)){
                    searchKeyword = searchKeyword.replace(/-/gi,"");
                    jQuery("#searchKeyword").val(searchKeyword);     //등록번호 형식일 경우 - -> "" 치환하여 text에 변환
                    jQuery("#searchQueryInput").val(searchKeyword);  //등록번호 형식일 경우 - -> "" 치환하여 [펼치기]에 변환 || 이 부분을 세팅 해줘야 [펼치기]하고서 출원번호, 등록번호 치환이 됨.
                }
                //입력된 숫자가 출원번호형식일 경우 "40-2003-0048429" 대쉬 제거 by lhy 2013.03.19
                var regExpRegNum3 = /^\d{2}-\d{4}-\d{7}$/;    
                if(regExpRegNum3.test(searchKeyword)){
                    searchKeyword = searchKeyword.replace(/-/gi,"");
                    jQuery("#searchKeyword").val(searchKeyword);     //출원번호 형식일 경우 - -> "" 치환하여 text에 변환
                    jQuery("#searchQueryInput").val(searchKeyword);  //출원번호 형식일 경우 - -> "" 치환하여 [펼치기]에 변환 || 이 부분을 세팅 해줘야 [펼치기]하고서 출원번호, 등록번호 치환이 됨.
                }
                /* ------------------------------------------------------------------- */                
                
		if (isVisibleQueryBox && textPosition == "TEXT") {
			if (trim(jQuery("#searchQueryInput").val()) != "") {
                                searchKeyword = trim(jQuery("#searchQueryInput").val()) ;
				jQuery("#searchKeyword").val(searchKeyword) ;
			}
		} else {
			textPosition = "INPUT" ;
		}
		if (textPosition == "INPUT") {
			searchKeyword = trim(jQuery("#searchKeyword").val()) ;
			if (isVisibleQueryBox) {
				jQuery("#searchQueryInput").val(searchKeyword) ;
			}
		}

		if (isKeywordValidation(searchKeyword)) {

			var expression = DelSpecialChar(searchKeyword) ;
			expression = removeOperatorBlank(expression) ;
			jQuery("#searchExpression").val(expression) ;

			switch (jQuery("#forwardSearchType").val()) {
				case "patent" :
					//jQuery("#totalSearchFrm").prop("action", "https://www.kipris.or.kr/kpat/resulta.do?next=ResultList") ;
                                        jQuery("#totalSearchFrm").prop("action", "https://www.kipris.or.kr/kpat/searchLogina.do?next=MainSearch&checkPot=Y") ;
					jQuery("#forwardQueryText").val(searchKeyword) ;
					jQuery("#forwardExpression").val(expression) ;
					jQuery("#forwardSortField1").val("") ;
					jQuery("#forwardSortState1").val("Asc") ;
					jQuery("#forwardConfig").val("G1111111111111111SSX11111111111111111") ;
					document.getElementById("totalSearchFrm").submit() ;
					break ;
				case "design" :
					jQuery("#totalSearchFrm").prop("action", "https://www.kipris.or.kr/kdtj/searchLogina.do?method=loginDG&checkPot=Y") ;
					jQuery("#forwardQueryText").val(searchKeyword) ;
					jQuery("#forwardExpression").val(expression) ;
					jQuery("#forwardSortField1").val("Score") ;
					jQuery("#forwardSortState1").val("Desc") ;
					jQuery("#forwardConfig").val("G1111111111111111111111S110001000000000000") ;
					document.getElementById("totalSearchFrm").submit() ;
					break ;
				case "trademark" :
					jQuery("#totalSearchFrm").prop("action", "https://www.kipris.or.kr/kdtj/searchLogina.do?method=loginTM&checkPot=Y") ;
					jQuery("#merchandiseString").val("td40,td41,td42,td43,td44,td45,td47,td48,tdmd,") ;
					jQuery("#measureString").val("A,B,J,R,F,I,C,G,") ;
					jQuery("#patternString").val("letter,figure,lmixed,fmixed,sounds,fragre,") ;
					jQuery("#forwardExpression").val("KW=[" + jQuery("#searchExpression").val() + "]") ;
					jQuery("#forwardQueryText").val("KW=[" + expression + "]") ;
					jQuery("#forwardConfig").val("G1111111111111111111111S110001000000000000") ;
					document.getElementById("totalSearchFrm").submit() ;
					break ;
				case "judgement" :
					jQuery("#totalSearchFrm").prop("action", "https://www.kipris.or.kr/kdtj/searchLogina.do?method=loginJM&checkPot=Y") ;
					jQuery("#forwardQueryText").val(searchKeyword) ;
					//jQuery("#forwardExpression").val("KW=[" + jQuery("#searchExpression").val() + "]") ;
                                        jQuery("#forwardExpression").val(jQuery("#searchExpression").val()) ;
					jQuery("#forwardConfig").val("G1111111111111111111111S110001000000000000") ;
					document.getElementById("totalSearchFrm").submit() ;
					break ;
				case "kpa" :
					jQuery("#totalSearchFrm").prop("action", "https://www.kipris.or.kr/kpa/search/search_kpa.do") ;
					jQuery("#totalSearchFrm").prop("target", "_blank") ;
					document.getElementById("totalSearchFrm").submit() ;
					break ;
				case "abpat" :
					jQuery("#totalSearchFrm").prop("action", "https://www.kipris.or.kr/abpat/searchLogina.do?next=MainSearch") ;
					jQuery("#forwardQueryText").val(searchKeyword) ;
					jQuery("#forwardCollectionValues").val("US_T.col,EP_T.col,WO_T.col,CN_T.col,GB_T.col,PAJ_T.col,DE_T.col,FR_T.col,AU_T.col,CA_T.col,RU_T.col,TW_T.col") ;
					document.getElementById("totalSearchFrm").submit() ;
					break ;
				case "abtm" :
					jQuery("#totalSearchFrm").prop("action", "https://www.kipris.or.kr/abtm/general.do?next=ResultList") ;
					jQuery("#forwardQueryText").val(searchKeyword) ;
					jQuery("#forwardExpression").val("KW=[" + expression + "]") ;
					jQuery("#forwardSortField").val("") ;
					jQuery("#forwardSortState").val("") ;
					jQuery("#forwardSortField1").val("Score") ;
					jQuery("#forwardSortState1").val("Desc") ;
					//jQuery("#forwardCollectionValues").val("US,JP,AU,CA") ;
                                        jQuery("#forwardCollectionValues").val("US,JP") ;
					jQuery("#forwardConfig").val("G01") ;
					jQuery("#forwardConfigChange").val("Y") ;
					document.getElementById("totalSearchFrm").submit() ;
					break ;
				case "abdg" :
					jQuery("#totalSearchFrm").prop("action", "https://www.kipris.or.kr/abdg/searchLogina.do?next=MainSearch") ;
					jQuery("#forwardQueryText").val(searchKeyword) ;
					jQuery("#forwardExpression").val("KW=[" + expression + "]") ;
                                        jQuery("#forwardCollectionValues").val("JP,US") ;
					jQuery("#forwardConfig").val("G01") ;
					jQuery("#forwardConfigChange").val("Y") ;
					document.getElementById("totalSearchFrm").submit() ;
					break ;	                                        
				default :

					try {
						setGooglePatentSearchResult(searchKeyword) ;
					}
					catch (e) { }

					try {
						document.title = "통합검색 (" + searchKeyword + ") < SEARCH - KIPRIS 특허정보 검색서비스" ;
					}
					catch (e) { }

					/* NDSL submit */
					try{
						if((typeof document.frmNdsl).toLowerCase() == 'object'){
							var frm = document.frmNdsl;

							jQuery("#searchResultNdsl").prop("action", "/kportal/search/search_ndsl.do") ;
							$('#ndslQueryText').val($('#searchKeyword').val());
							$('#ndslExpression').val($('#searchExpression').val());
							$('#ndslQuery').val(searchKeyword);
							$('#ndslDisplayCount').val($('#opt28').val());
							$('#ndslCategory').val(frm.category.value);
							jQuery("#searchResultNdsl").submit() ;
							return false;
						}
					}
					catch(e){

					}
                                        
                                        //By J.H.S 20140807 결과내 재검색시 검색 히스토리에 넣을 값
					if (jQuery("#innerSearchCk").prop("checked")) {
                                            searchKeyword = "(" + jQuery("#beforeExpression").val() + ")*" + searchKeyword;
					}
                                        //웹취약점 조치를 위해 < , > 문자 제거 
					appendSearchKeywordHistory(KIPRIS_TOTAL_HISTORY_KEY, searchKeyword.replace(/</gi,"").replace(/>/,""), 10) ;
					setSearchKeywordHistoryBoard() ;

					totalSearchCount = 0 ;
                                        totalSearchCountIpNavi =0;
                                        
					resetSearchCountingBoard() ;

					jQuery("#searchIndex").hide() ;
					jQuery("#searchError").hide() ;

					isSearchExtends = jQuery("#searchInTransCk").prop("checked") ;

					var searchKeyword = jQuery("#searchKeyword").val() ;
                                        
					if (isVisibleQueryBox) {
						if (trim(jQuery("#searchQueryInput").val()) != "") {
							searchKeyword = jQuery("#searchQueryInput").val() ;
						}
					}

					if (jQuery("#innerSearchCk").prop("checked")) {
						//By J.H.S 20140807 결과내 재검색시 inputText에 표시할 사용자 최종 검색어
						jQuery("#searchKeyword").val("(" + jQuery("#beforeExpression").val() + ")*"+ jQuery("#searchExpression").val()) ;
                                                jQuery("#searchExpression").val("(" + jQuery("#beforeExpression").val() + ")*"+ jQuery("#searchExpression").val()) ;
					}

					jQuery("#beforeExpression").val(jQuery("#searchExpression").val()) ;
					jQuery('#strstat').val("TOP|KW");

//					jQuery("#resultQuery").val(jQuery("#searchKeyword").val()) ;
					jQuery("#resultQuery").val(searchKeyword) ;
					jQuery("#resultExpression").val(jQuery("#searchExpression").val()) ;
					jQuery("#resultExtends").val((isSearchExtends) ? "Y" : "N") ;
					jQuery("#resultSearchInTransKorToEng").val((isSearchExtends) ? "Y" : "N") ;
					jQuery("#resultSearchInTransEngToKor").val((isSearchExtends) ? "Y" : "N") ;

					
					var eSearchKeyword = encodeURL(searchKeyword);
					var eSearchExpression = encodeURL(jQuery("#searchExpression").val());
					
					getPatentSearchResult(eSearchKeyword, eSearchExpression);
					getDesignSearchResult(eSearchKeyword, eSearchExpression);
					getTrademarkSearchResult(eSearchKeyword, eSearchExpression);
					getFrnUSSearchResult(eSearchKeyword, eSearchExpression);
					getFrnEUSearchResult(eSearchKeyword, eSearchExpression);
					//getFrnPCTSearchResult(eSearchKeyword, eSearchExpression);
					getFrnJPSearchResult(eSearchKeyword, eSearchExpression);
					//getFrnCNSearchResult(eSearchKeyword, eSearchExpression);
					//getFrnENSearchResult(eSearchKeyword, eSearchExpression);
					//getFrnDESearchResult(eSearchKeyword, eSearchExpression);
					//getFrnFRSearchResult(eSearchKeyword, eSearchExpression);
					//getFrnAUSearchResult(eSearchKeyword, eSearchExpression));
					//getFrnCASearchResult(eSearchKeyword, eSearchExpression);
					//getFrnRUSearchResult(eSearchKeyword, eSearchExpression);
					//getFrnTWSearchResult(eSearchKeyword, eSearchExpression);
                    getNdslArticleSearchResult(eSearchKeyword, eSearchExpression);
                    getNdslJournalSearchResult(eSearchKeyword, eSearchExpression);

                    // IPNAVI 추가
					getIpNaviPrcdnSearchResult(eSearchKeyword, eSearchExpression);
					getIpNaviConflictSearchResult(eSearchKeyword, eSearchExpression);

					//getIpNaviGuidebookSearchResult(eSearchKeyword, eSearchExpression);
                                        
					isPageError = false ;
					break ;
			}
		} else {
		}
	}
	catch(e) {
		isPageError = true ;
		printTotalSearchException(e) ;
	}
}

jQuery("#totalSearchFrm").submit(
		function(evt) {
			//By J.H.S 20140106 검색어 입력을 안했을 경우  
                        var queryTextCheck = jQuery("#searchKeyword").val();      
                        var searchQueryInput = jQuery("#searchQueryInput").val(); 
                        if((queryTextCheck =="" || queryTextCheck == null) && (searchQueryInput =="" || searchQueryInput == null)){
                            alert("검색어를 입력해 주십시요.");
                            jQuery("#searchKeyword").focus();
                            return false;
                        }
                        // ----------------------------  //
                        evt.preventDefault() ;
			resetSearchOption() ;
			goTotalSearching() ;
                        
                        //By J.H.S 20130718 선택항목 체크된 값 초기화.
                        jQuery("#NWBOOKMARK", "#searchResultPageFrm").val("");
                        //By J.H.S 선택해제로 되있을경우 검색버튼을 누르면 선택보기로 바꾸기위함.
                        jQuery("#showAllCheckArticleBtnContainer").hide() ;   //선택해제 이미지 숨기고
			jQuery("#showOnlyCheckArticleBtnContainer").show() ;  //선택하기 이미지 보이기
                        isBookmarkView = false ;  //false 해줘야 재검색후에 선택하기 기능이 적용됨.
                        /* ******************************************************** */
		}
	) ;

function alertTotalSearchException(e) {
	alert(e) ;
}

function printTotalSearchException(e) {

	isPageError = true ;

	var emptyTag = "<li>" ;
	emptyTag += "<div class=\"search_blank\"></div>" ;
	emptyTag += "</li>" ;

	jQuery("#searchIndex").hide() ;

	jQuery("#resultPatent").hide() ;
	jQuery("#patentResultCountBoard").empty() ;
	jQuery("#patentResultList").empty().append(emptyTag) ;

	jQuery("#resultDesign").hide() ;
	jQuery("#designResultCountBoard").empty() ;
	jQuery("#designResultList").empty().append(emptyTag) ;

	jQuery("#resultTrademark").hide() ;
	jQuery("#trademarkResultCountBoard").empty() ;
	jQuery("#trademarkResultList").empty().append(emptyTag) ;

	jQuery("#resultFrnUS").hide() ;
	jQuery("#frnUSResultCountBoard").empty() ;
	jQuery("#frnUSResultList").empty().append(emptyTag) ;

	jQuery("#resultFrnEU").hide() ;
	jQuery("#frnEUResultCountBoard").empty() ;
	jQuery("#frnEUResultList").empty().append(emptyTag) ;

//	jQuery("#resultFrnPCT").hide() ;
//	jQuery("#frnPCTResultCountBoard").empty() ;
//	jQuery("#frnPCTResultList").empty().append(emptyTag) ;

	jQuery("#resultFrnJP").hide() ;
	jQuery("#frnJPResultCountBoard").empty() ;
	jQuery("#frnJPResultList").empty().append(emptyTag) ;

//	jQuery("#resultFrnCN").hide() ;
//	jQuery("#frnCNResultCountBoard").empty() ;
//	jQuery("#frnCNResultList").empty().append(emptyTag) ;

//	jQuery("#resultFrnEN").hide() ;
//	jQuery("#frnENResultCountBoard").empty() ;
//	jQuery("#frnENResultList").empty().append(emptyTag) ;

//	jQuery("#resultFrnDE").hide() ;
//	jQuery("#frnDEResultCountBoard").empty() ;
//	jQuery("#frnDEResultList").empty().append(emptyTag) ;

//	jQuery("#resultFrnFR").hide() ;
//	jQuery("#frnFRResultCountBoard").empty() ;
//	jQuery("#frnFRResultList").empty().append(emptyTag) ;

//	jQuery("#resultFrnAU").hide() ;
//	jQuery("#frnAUResultCountBoard").empty() ;
//	jQuery("#frnAUResultList").empty().append(emptyTag) ;

//	jQuery("#resultFrnCA").hide() ;
//	jQuery("#frnCAResultCountBoard").empty() ;
//	jQuery("#frnCAResultList").empty().append(emptyTag) ;

//	jQuery("#resultFrnRU").hide() ;
//	jQuery("#frnRUResultCountBoard").empty() ;
//	jQuery("#frnRUResultList").empty().append(emptyTag) ;

//	jQuery("#resultFrnTW").hide() ;
//	jQuery("#frnTWResultCountBoard").empty() ;
//	jQuery("#frnTWResultList").empty().append(emptyTag) ;

        // IPNAVI 추가
	jQuery("#resultIpnaviPrcdn").hide() ;
	jQuery("#ipnaviPrcdnResultCountBoard").empty() ;
	jQuery("#ipnaviPrcdnResultList").empty().append(emptyTag) ;

	jQuery("#resultIpnaviConflict").hide() ;
	jQuery("#ipnaviConflictResultCountBoard").empty() ;
	jQuery("#ipnaviConflictResultList").empty().append(emptyTag) ;
        
	//jQuery("#resultIpnaviGuidebook").hide() ;
	//jQuery("#ipnaviGuidebookResultCountBoard").empty() ;
	//jQuery("#ipnaviGuidebookResultList").empty().append(emptyTag) ;
        
	jQuery("#searchError").show() ;
	jQuery("#searchErrorMessage").text(e) ;

}

</script>
<form name="biblioF" method="post">
<input type="hidden" name="applno" value="" />
<input type="hidden" name="index" value="" />
<input type="hidden" name="kindOfReq" value="" />
<input type="hidden" name="isMyConcern" value="" />
<input type="hidden" name="isMyFolder" value="" />
<input type="hidden" name="query" value="" />
<input type="hidden" name="expression" value="" />
<input type="hidden" name="sortField1" value="" />
<input type="hidden" name="sortField2" value="" />
<input type="hidden" name="sortState1" value="" />
<input type="hidden" name="sortState2" value="" />
<input type="hidden" name="searchInTrans" value="" />
<input type="hidden" name="currentPage" value="" />
<input type="hidden" name="searchFg" value="" />
<input type="hidden" name="collections" value="" />
<input type="hidden" name="rights" value="" />
<input type="hidden" name="merchandiseString" value="" />
<input type="hidden" name="start" value="" />
<input type="hidden" name="numPerPage" value="" />
<input type="hidden" name="sortField"           value=""/>
<input type="hidden" name="sortState"           value=""/>
<input type="hidden" name="FROM"                value=""/>
<input type="hidden" name="BOOKMARK"            value=""/>
<input type="hidden" name="REBOOKMARK"          value=""/>
<input type="hidden" name="pub_reg">
<input type="hidden" name="cntry">
<input type="hidden" name="next"                value="biblioFrame"/>
<input type="hidden" name="openPageId"          value="View01"/>
<input type="hidden" id="highlightKeyword"      name="highlightKeyword" value=""/>
     <!--유사특허 by.2017.06-->
     <input type="hidden" name="checkPot"         value=""/>
     <input type="hidden" name="queryText"         value=""/>
</form>
<script type="text/javascript">

function openDetail(applno, index, applnoLinks, start, numPerPage, openPageId)
{
	var theForm = document.biblioF ;
	theForm.applno.value = applno ;
	theForm.index.value = index ;
	theForm.openPageId.value = openPageId ;
	theForm.expression.value = jQuery("#resultExpression").val() ;
	
	var expr = theForm.expression.value;
	if (expr.indexOf("\"") >= 0)
	{
		theForm.expression.value = expr.replace(/\"/g, "&#34;");
	}
	
	theForm.sortField1.value = "" ;
	theForm.sortField2.value = "" ;
	theForm.sortState1.value = "" ;
	theForm.sortState2.value = "" ;
	//20200715 서지정보 열때 현재 보이는 목록을 기준으로 열어여 함으로 이전 검색어확장 param을 불러옴
	theForm.searchInTrans.value = document.searchResultFrm.resultExtends.value;  
    theForm.currentPage.value = (document.getElementById("searchResultSearchPage") ? jQuery("#searchResultSearchPage").val() : "1") ; //By J.H.S 20140624 페이지 이동에 따른 현재페이지 넘기기
    theForm.highlightKeyword.value = (document.getElementById("highlightKeyword") ? jQuery("#highlightKeyword").val() : "") ; //20220929 하이라이트
	theForm.searchFg.value = "Y";  //By J.H.S 20131028 특실 left 리스트 들고오도록 설정
	theForm.start.value = start;
	theForm.numPerPage.value = numPerPage;
	biblioOpen() ;
	return void 0 ;
}
var kpatBiblioWindow = null ;
function biblioOpen()
{
	/* 다중창 서비스 제공으로 수정 202309 KJW
	if (kpatBiblioWindow == null || kpatBiblioWindow.closed)
	{
		kpatBiblioWindow = window.open("", "kpatBiblioWin", "scrollbars=0,resizable=yes,width=1000,height=845");
		kpatBiblioWindow.focus() ;
	}
	else
	{
		kpatBiblioWindow.close() ;
		kpatBiblioWindow = window.open("", "kpatBiblioWin", "scrollbars=0,resizable=yes,width=1000,height=845");
		kpatBiblioWindow.focus() ;
	} */
	
	var biblioF = document.biblioF;
	var applno = biblioF.applno.value;
	
	kpatBiblioWindow = window.open("", applno, "scrollbars=0,resizable=yes,width=1024,height=875");
	kpatBiblioWindow.focus() ;
	
	biblioF.method = "post";
	// biblioF.target = "kpatBiblioWin";
	biblioF.target = applno;
	biblioF.action = "https://www.kipris.or.kr/kpat/biblioa.do?method=biblioFrame";
	biblioF.submit();
	biblioF.target = "";
}

//해외특허 [공고전문], [행정진행정보] Open 함수 //
function openDetailAbpat(VdkVgwKey, Collection, Page, Country, Index, OpenPageId) {
	var theForm = document.foreignViewFrm ;
        var viewWin = newPopupWindow("", "biblioWin", 1000, 825, "C", "M", "resizable=yes") ;
        
        theForm.query.value = jQuery("#resultQuery").val() ;
        theForm.expression.value = jQuery("#resultExpression").val() ;

	if (Country == "JP")
	{
		// 일본은 PJ를 약자로 쓰게 되어있음..
		// 2012.11.21 bhhan
		theForm.cntry.value = "PJ" ;
	}
	else
		theForm.cntry.value = Country ;
        
        //OpenPageId "" 이거나 null 이면 전문페이지로 가도록 설정.
        if(OpenPageId == "" || OpenPageId == null){
            OpenPageId = "View03";
        }

	theForm.publ_key.value = VdkVgwKey ;
	theForm.index.value = Index ;
	theForm.currentPage.value = Page ;
	theForm.collectionValues.value = Collection ;
        //theForm.openPageId.value = "View03"; //전문정보페이지 2013.04.02 jhs
        theForm.openPageId.value = OpenPageId;
	theForm.target = "biblioWin" ;
	theForm.submit() ;
	viewWin.focus() ;
}

var fileCheckTrans = null ;
function goFileCheckTrans(appl, pub_reg, fp, ANLIST, PKLIST) {
	var url = "http://trans.kipris.or.kr/translation/PTRN/index.jsp?AN=" + appl + "&PK=" + pub_reg + "&ANLIST=" + ANLIST + "&PKLIST=" + PKLIST + "&FP=" + fp;
	if (fileCheckTrans) {
		fileCheckTrans.close();
	}
	fileCheckTrans = window.open(url, "fileCheckTrans", "status=yes,  width=960, height=734 , status=yes, scrollbars=no, resizable=no, menubar=no");
	return void 0 ;
}

function viewPatent(N, P, idx) {

	var viewWin = newPopupWindow("", "patentBiblioViewWin", 1000, 825, "C", "M", "resizable=yes") ;
	var F = document.patentViewFrm ;
	F.index.value = idx ;
	F.currentPage.value = P ;
	F.applno.value = N ;
	F.expression.value = jQuery("#patentExpression").val() ;
	F.target = "patentBiblioViewWin" ;
	F.submit() ;
	viewWin.focus() ;

}

var BiblioWindow = null ;
//20141208 pdy 국제등록번호 추가
function GoBibliography(pat, masterKey, index, kindOfReq, valid_fg, openPageId, hn)
{
	var form = document.designViewFrm;
	//form.target = "BiblioWindowDTJ";
	form.target = masterKey;
	form.openPageId.value = openPageId;
	form.kindOfReq.value = kindOfReq;
	form.isMyConcern.value = "N";
	form.isMyFolder.value = "N";
	form.searchFg.value = "Y";

	var iQuery = jQuery("#resultQuery").val() ;
	var iExpression = jQuery("#resultExpression").val() ;
	//form.searchInTrans.value = jQuery("#searchInTransCk").prop("checked")? "Y": "N" ;
	//20200715 서지정보 열때 현재 보이는 목록을 기준으로 열어여 함으로 이전 검색어확장 param을 불러옴
	form.searchInTrans.value = document.searchResultFrm.resultExtends.value;  
        
	if (pat == "TM")
	{
		if (iExpression.indexOf("\"")>=0)
		{
			iExpression=iExpression.replaceAll("\"","&#34;");
        }
		
		if (iQuery.indexOf("=[") > -1)
		{
			form.query.value = iQuery ;
		}
		else
		{
			form.query.value = "KW=[" + iQuery + "]" ;
		}
		
		if (iExpression.indexOf("=[") > -1)
		{
			form.expression.value = iExpression ;
		}
		else
		{
			form.expression.value = "KW=[" + iExpression + "]" ;
		}
		form.config.value = "G11111111111111111SX11111001111110";
		//form.config.value = "G11111111111111111SX01111111111111" ;
		form.merchandiseString.value = "td40,td41,td42,td43,td44,td45,td47,td48,tdmd," ;
	}
	else
	{
		//검색어 키워드 조합이 누락되어 수정함. By j.h.s 20130329
		if (iQuery.indexOf("=[") > -1)
		{
			form.query.value = iQuery ;
		}
		else
		{
			form.query.value = "KW=[" + iQuery + "]" ;
		}
		
		if (iExpression.indexOf("=[") > -1)
		{
			form.expression.value = iExpression ;
		}
		else
		{
			form.expression.value = "KW=[" + iExpression + "]" ;
		}
		//form.query.value = iQuery ;
		//form.expression.value = iExpression ;
		form.config.value = "G11111111111111111SX11100110011011110" ;
		//form.config.value = "G11111111111111111SX10000110011101011" ;
		form.merchandiseString.value = "" ;
	}
	
	form.sortField1.value = "" ;
	form.sortField2.value = "" ;
	form.sortState1.value = "Asc" ;
	form.sortState2.value = "Asc" ;
	//20200715 상단에서 searchInTrans 값을 지정하고있어서 필요없는 아래 부분 주석 처리
	//form.searchInTrans.value = "N" ;
	form.currentPage.value = (document.getElementById("searchResultSearchPage") ? jQuery("#searchResultSearchPage").val() : "1") ;
	form.collections.value = "" ;
	form.rights.value = pat;
	form.numPerPage.value = (jQuery("#opt28").val() ? jQuery("#opt28").val() : "30");  //By J.H.S 20140624 페이지당(30, 60, 90)보기 값 넘기기
        
	//20141208 pdy 국제등록번호 추가
	if (hn != null && hn.length>1)
	{
		form.action = "https://www.kipris.or.kr/kdtj/grrt1000a.do?method=biblio" + pat + "Frame&masterKey=" + masterKey + "&index=" + index + "&kindOfReq=" + kindOfReq + "&valid_fg=" + valid_fg + "&hn=" + hn;
	}
	else
	{
		form.action = "https://www.kipris.or.kr/kdtj/grrt1000a.do?method=biblio" + pat + "Frame&masterKey=" + masterKey + "&index=" + index + "&kindOfReq=" + kindOfReq + "&valid_fg=" + valid_fg;
	}
	
	/* 다중창 서비스 제공으로 수정 202309 KJW
	if (BiblioWindow == null || BiblioWindow.closed)
	{
		BiblioWindow = window.open("", "BiblioWindowDTJ", "resizable=yes,width=1000,height=825");
		BiblioWindow.focus();
	}
	else
	{
		BiblioWindow.close();
		BiblioWindow = window.open("", "BiblioWindowDTJ", "resizable=yes,width=1000,height=825");
		BiblioWindow.focus();
	} */
	
	BiblioWindow = window.open("", masterKey, "resizable=yes,width=1024,height=875");
	BiblioWindow.focus();
	
	form.submit() ;
	form.target = "" ;
}

function viewDesign(N, T, P, idx) {

	var viewWin = newPopupWindow("", "BiblioWindowDTJ", 1000, 825, "C", "M", "resizable=yes") ;
	var F = document.designViewFrm ;
        F.searchInTrans.value = jQuery("#searchInTransCk").prop("checked")? "Y": "N" ;
	F.query.value = jQuery("#resultQuery").val() ;
	F.expression.value = jQuery("#resultExpression").val() ;
	F.index.value = idx ;
	F.masterKey.value = N ;
	F.currentPage.value = P ;
	F.rights.value = T ;
	F.target = "BiblioWindowDTJ" ;
	F.action = "https://www.kipris.or.kr/kdtj/grrt1000a.do?method=biblio" + T + "Frame" ;
	F.submit() ;
	viewWin.focus() ;

}
function viewTrademark(N, T, P, idx) {

	var viewWin = newPopupWindow("", "BiblioWindowDTJ", 1000, 825, "C", "M", "resizable=yes") ;
	var F = document.designViewFrm ;
        F.searchInTrans.value = jQuery("#searchInTransCk").prop("checked")? "Y": "N" ;
	F.query.value = jQuery("#resultQuery").val() ;
	F.expression.value = jQuery("#resultExpression").val() ;
	F.index.value = idx ;
	F.masterKey.value = N ;
	F.currentPage.value = P ;
	F.rights.value = T ;
	F.target = "BiblioWindowDTJ" ;
	F.action = "https://www.kipris.or.kr/kdtj/grrt1000a.do?method=biblio" + T + "Frame" ;
	F.submit() ;
	viewWin.focus() ;

}

function viewForeignPatent(N, L, P, C, idx)
{
	var F = document.foreignViewFrm ;
	F.query.value = jQuery("#resultQuery").val() ;
	F.expression.value = jQuery("#resultExpression").val() ;
	F.queryText.value = jQuery("#resultExpression").val() ;
	
	var query = F.query.value;
	var expression = F.expression.value;
	if (expression.indexOf("\"")>=0)
	{
		F.expression.value = expression.replaceAll("\"","&#34;");
		F.query.value = query.replaceAll("\"","&#34;");
	}
	if (C == "JP")
	{
		// 일본은 PJ를 약자로 쓰게 되어있음..
		// 2012.11.21 bhhan
		F.cntry.value = "PJ" ;
		F.collectionValues.value = "PAJ_T.col," ;
	}
	else
	{
		F.cntry.value = C ;
		F.collectionValues.value = L ;
	}
        
	//F.searchInTrans.value = jQuery("#searchInTransCk").prop("checked")? "Y": "N" ;
	//20200715 서지정보 열때 현재 보이는 목록을 기준으로 열어여 함으로 이전 검색어확장 param을 불러옴
	F.searchInTrans.value = document.searchResultFrm.resultExtends.value;  
	F.publ_key.value = N ;
	F.index.value = idx ;
	F.currentPage.value = P ;
	F.openPageId.value = "View01";  //서지정보페이지 2013.04.02 jhs
	F.numPerPage.value = (jQuery("#opt28").val() ? jQuery("#opt28").val() : "30");  //By J.H.S 20140624 페이지당(30, 60, 90)보기 값 넘기기
	
	/* 다중창 서비스 제공으로 수정 202309 KJW
	var viewWin = newPopupWindow("", "biblioWin", 1000, 825, "C", "M", "resizable=yes");
	F.target = "biblioWin"; */
	var viewWin = newPopupWindow("", N, 1024, 875, "C", "M", "resizable=yes");
	F.target = N;
	
	F.submit() ;
	viewWin.focus() ;
}

var bigFrontDraw = null ;
function OpenFrontDrawPop(applno)
{
	/* 다중창 서비스 제공으로 수정 202309 KJW
	if (bigFrontDraw)
	{
		try
		{
			bigFrontDraw.close() ;
		}
		catch (e) {}
		bigFrontDraw = null ;
	}
	bigFrontDraw = window.open("https://www.kipris.or.kr/kpat/biblio/biblioFrontDrawPop.jsp?applno=" + applno, "bigFrontDraw", "width=1024, height=768, left=10, top=10, resizable=yes, scrollbars=yes, status=yes"); */
	bigFrontDraw = window.open("https://www.kipris.or.kr/kpat/biblio/biblioFrontDrawPop.jsp?applno=" + applno, "bigFrontDraw-" + applno, "width=1024, height=768, left=10, top=10, resizable=yes, scrollbars=yes, status=yes");
	bigFrontDraw.focus() ;
}

function OpenFrontDrawPopABPAT(publ_key, cntry)
{
	// 이용현황 통계 추가 by2018.07.26
	// SaveOpsvcData('KR', 'ABPAT', 'OPSVC', 'IMZM');
    
	/* 다중창 서비스 제공으로 수정 202309 KJW
    if (bigFrontDraw == null || bigFrontDraw.closed)
    {
        bigFrontDraw = window.open("https://www.kipris.or.kr/abpat/remoteFile.do?method=bigFrontDraw&publ_key="+ publ_key+"&cntry="+ cntry, "bigFrontDraw", "width=1024, height=768, left=10, top=10, resizable=yes, scrollbars=yes, status=yes");
        bigFrontDraw.focus();
    }
    else
    {
        bigFrontDraw.close();
        bigFrontDraw = window.open("https://www.kipris.or.kr/abpat/remoteFile.do?method=bigFrontDraw&publ_key="+ publ_key+"&cntry="+ cntry, "bigFrontDraw", "width=1024, height=768, left=10, top=10, resizable=yes, scrollbars=yes, status=yes");
        bigFrontDraw.focus();
    } */
    
	bigFrontDraw = window.open("https://www.kipris.or.kr/abpat/remoteFile.do?method=bigFrontDraw&publ_key="+ publ_key + "&cntry="+ cntry, "bigFrontDraw"+ publ_key, "width=1024, height=768, left=10, top=10, resizable=yes, scrollbars=yes, status=yes");
    bigFrontDraw.focus();
}


/* By J.H.S 20140303 특허.실용신안 IPC 분류코드 조회링크 추가 */
function remoconOpenKpat(kind, start, ipcCode)
{
    var remoconHelpWindow;
    var result_ipc;
    var detail_ipc;
    var index_ipc;
    var index_tmp_ipc;
    
    if (ipcCode != "")
        ipcCode= ipcCode.replace(" ","");
    
    //var url = "/kpat/remocon/frame.jsp?kind=" + kind + "&start=" + start + "&IPC_CODE=" + ipcCode;
    var url = "http://www.kipris.or.kr/kpat/remocon/frame.jsp?kind=" + kind + "&start=" + start + "&IPC_CODE=" + ipcCode;

    remoconHelpWindow = window.open(url,"remocon","height=750,width=855,status=yes,toolbar=no,menubar=no,location=no,scrollbars=yes");
}

/* By J.H.S 20140303 디자인,상표 - 디자인 분류코드, 상품분류, 도형코드 조회링크 추가 */
function remoconOpenDTJ(kind, start, menuKind, userid,  rtField, rights)
{
    var remoconHelpWindow;
    
    var url = "http://www.kipris.or.kr/kdtj/remocon/frame.jsp?kind=" + kind + "&start=" + start + "&userid="+userid+"&menuKind="+menuKind+"&rtField="+rtField+"&rights="+rights;
    //var url = "/kdtj/remocon/frame.jsp?kind=" + kind + "&start=" + start + "&userid="+userid+"&menuKind="+menuKind+"&rtField="+rtField+"&rights="+rights;

    remoconHelpWindow = window.open(url,"remocon","height=750,width=880,status=yes,toolbar=no,menubar=no,location=no");
}

/* By J.H.S 20140303 해외특허 IPC, CPC 분류코드 조회링크 추가 */
function remoconOpenAbpat(kind, start, ipcCode)
{
       var code_Sel_str = "";
       if (ipcCode != "")
           ipcCode= ipcCode.replace(" ","");
           
       var url = "http://www.kipris.or.kr/abpat/remocon/frame.jsp?kind=" + kind + "&start=" + start + "&IPC_CODE=" + ipcCode;
       //var url = "/abpat/remocon/frame.jsp?kind=" + kind + "&start=" + start + "&IPC_CODE=" + ipcCode;
    
       if(kind == 2){ //항목별검색-검색도우미(팝업)
           remoconWindow = window.open(url,"remocon","width=855,height=750,status=yes,toolbar=no,menubar=no,location=no");
       }else{
           remoconWindow = window.open(url,"remocon","width=855,height=750,status=yes,toolbar=no,menubar=no,location=no");
       }
}

</script>
<form name="patentViewFrm" id="patentViewFrm" method="post" action="https://www.kipris.or.kr/kpat/biblioa.do?method=biblioFrame">
<input type="hidden" name="applno" value="" />
<input type="hidden" name="index" value="" />
<input type="hidden" name="searchFg" value="Y" />
<input type="hidden" name="expression" value="" />
<input type="hidden" name="start" value="biblio" />
<input type="hidden" name="sortField1" value="Score" />
<input type="hidden" name="sortState1" value="Desc" />
<input type="hidden" name="sortField2" value="" />
<input type="hidden" name="sortState2" value="" />
<input type="hidden" name="searchInTrans" value="N" />
<input type="hidden" name="next" value="biblioFrame" />
<input type="hidden" name="currentPage" value="1" />
<input type="hidden" name="numPerPage" value="30" />
<input type="hidden" name="config" value="G1111111111111111SSX11111111111111111" />
</form>
<form name="designViewFrm" id="designViewFrm" method="post">
<input type="hidden" name="openPageId" value="View01" />
<input type="hidden" name="masterKey" value="" />
<input type="hidden" name="index" value="" />
<input type="hidden" name="kindOfReq" value="A" />
<input type="hidden" name="isMyConcern" value="N" />
<input type="hidden" name="isMyFolder" value="N" />
<input type="hidden" name="searchFg" value="Y" />
<input type="hidden" name="query" value="" />
<input type="hidden" name="expression" value="" />
<input type="hidden" name="sortField1" value="" />
<input type="hidden" name="sortField2" value="" />
<input type="hidden" name="sortState1" value="Asc" />
<input type="hidden" name="sortState2" value="Asc" />
<input type="hidden" name="searchInTrans" value="N" />
<input type="hidden" name="currentPage" value="1" />
<input type="hidden" name="collections" value="" />
<input type="hidden" name="rights" value="" />
<input type="hidden" name="numPerPage" value="30" />
<input type="hidden" name="next" value="biblioFrame" />
<input type="hidden" name="merchandiseString" value="td40,td41,td42,td43,td44,td45,td47,td48,tdmd," />
<input type="hidden" name="config" value="" />
</form>
<form name="foreignViewFrm" id="foreignViewFrm" method="post" action="https://www.kipris.or.kr/abpat/biblioa.do?method=biblioFrame">
<input type="hidden" name="index" value="" />
<input type="hidden" name="openPageId" value="View01" />
<input type="hidden" name="start" value="biblio" />
<input type="hidden" name="searchFg" value="Y" />
<input type="hidden" name="query" value="" />
<input type="hidden" name="expression" value="" />
<input type="hidden" name="publ_key" value="" />
<input type="hidden" name="cntry" value="" />
<input type="hidden" name="sortField1" value="Score" />
<input type="hidden" name="sortField2" value="" />
<input type="hidden" name="sortState1" value="Desc" />
<input type="hidden" name="sortState2" value="" />
<input type="hidden" name="searchInTrans" value="" />
<input type="hidden" name="currentPage" value="1" />
<input type="hidden" name="collectionValues" value="" />
<input type="hidden" name="numPerPage" value="30" />
<input type="hidden" name="next" value="biblioFrame" />
<input type="hidden" name="config" value="" />
<input type="hidden" name="queryText" value="" />
</form>
<!--<p class="smartsearch_info"><img src="/kportal/images/common/smartsearch_info.png"  alt="항목별 검색을 위해 스마트검색(구 항목별검색)을 열어보세요" /></p>-->
	</header>
	<hr/>
	<div id="body">
		

<section id="f_smart_finder">
	<!-- 스마트 파인더, 고급검색 오픈 -->
	<div id="f_smartSearcherContainer">
		<div id="f_divSmartFinder" class="detail_smart" >
			<form id="f_smartSearchFrm" method="post">
				<div class="helpme_info"><em class="point02 txt_bold">통합검색 키워드입력창</em> 입니다. 검색할 단어를 입력해주세요.</div>
				<div class="code_search">
					<span><label for="f_searchInclude" class="txt_bold">반드시포함</label> <input name="searchInclude" id="f_searchInclude" type="text" value="" class="input_small" style="ime-mode:active;"/></span>
					<span><label for="f_searchExcept" class="txt_bold">제외단어</label> <input name="searchExcept" id="f_searchExcept" type="text" value="" class="input_small" style="ime-mode:active;"/></span>
					<!--span class="code_check"><input name="searchCode" id="f_searchCode" type="checkbox" value="0" /> <label for="f_searchCode">코드검색</label></span-->
				</div>
				<p class="code_search_info"><span class="display_block">원하는 검색결과에 맞춰 키워드를 입력하시면 됩니다. (입력창 모두를 입력하실 필요는 없습니다.)</span>
					<!--코드검색을 선택하시면 한영/영한 번역검색이 불가능합니다.--></p>
				<div class="btn_area">
					<!--<img src="/kportal/images/button/btn_helpme.gif" alt="검색정보입력도우미"/>-->
				<button title="검색하기" type="submit"><img src="/kportal/images/button/btn_search.gif" alt="검색하기"/></button></div>
                                <div class="tip_help"><img src="/kportal/images/common/kportal_search1.png" alt="권리별 스마트 검색에서는 보다 자세한 검색을 제공합니다."> </div>
			</form>
		</div>
	</div>
	<!-- //스마트 파인더, 고급검색 오픈 -->
	<!-- 스마트 파인더, 고급검색 기본 -->
	<div class="sfinder_open">
                <span class="sfinder_btn_left">
                        <a id="btnToggleSmartFinder2" href="javascript:f_smartSearchForm()">
                                <img id="ToggleSmartFinder2" src="/kportal/images/common/btn_smartfinder_open_left.gif" alt="스마트검색"/>
                        </a>
                </span>
		<span id="f_smartSearchOpenBtn" class="sfinder_txt"><img id="f_smartSearcherOpenImg" src="/kportal/images/common/btn_smartfinder_open_m.gif" alt="항목별 검색을 위해 이곳을 클릭해주세요"/>
		<img id="f_smartSearcherCloseImg" src="/kportal/images/common/btn_smartfinder_close.gif" alt="스마트검색 닫기 ▲"/></span>
		<span class="Cscroll_stop">
			<a href="javascript:hideFlowingSmartForm()" title="자동스크롤 끄기"><img id="f_btnAutoScrollOff" src="/kportal/images/common/txt_Cscroll_stop.gif" alt="자동스크롤 끄기" /></a>
		</span>
	</div>
	<!-- //스마트 파인더, 고급검색 기본 -->
</section>
<script type="text/javascript">

	jQuery("#f_smartSearchFrm").submit(
		function(evt) {
		        evt.preventDefault() ;
		        //f_smartSearcherClose(); //주석을 해제하면 자동스크롤 스마트검색으로 검색시 스마트검색창을 닫고 검색함.
		        //By J.H.S 20131126 스마트검색의 [검색하기] 버튼 클릭시 검색서비스 안내를 숨기는 것을 추가함.
		        jQuery("#searchIndex").hide() ;
		        // ******************** //
		
		        //상단 검색 placeholder hidden By J.H.S 20131022 추가
		        //$('#ol_queryTextlabel').css('visibility','hidden');
		
			jQuery("#searchInclude").val(jQuery("#f_searchInclude").val()) ;
			jQuery("#searchExcept").val(jQuery("#f_searchExcept").val()) ;
		
			try {
		          	smartSearchSubmission() ;
				isPageError = false ;
			} catch(e) {
				printTotalSearchException(e) ;
			}
	});

	function hideFlowingSmartForm() {
		if (isAutoScrollSmartSearcherOpened) {
			jQuery("#f_smartSearcherContainer").animate({ height : 0 }, 190
				, function() {
					jQuery("#f_smart_finder").animate({top: (0 - jQuery("#f_smart_finder").height())}, 330
							, function() {
								jQuery("#f_divSmartFinder").hide() ;
								jQuery("#f_smartSearcherCloseImg").hide() ;
								jQuery("#f_smartSearcherOpenImg").show() ;
								jQuery("#f_smart_finder").css({"top":"-1000px"}) ;
							});
				});
		} else {
			jQuery("#f_smart_finder").animate({top: (0 - jQuery("#f_smart_finder").height())}, 330
					, function() {
						jQuery("#f_divSmartFinder").hide() ;
						jQuery("#f_smartSearcherCloseImg").hide() ;
						jQuery("#f_smartSearcherOpenImg").show() ;
						jQuery("#f_smart_finder").css({"top":"-1000px"}) ;
					});
        }
		isAutoScrollingSmartSearcher = false ;
		jQuery("#btnAutoScrollOff").hide() ;
		jQuery("#btnAutoScrollOn").show() ;
	}

	isAutoScrollingSmartSearcher = false ;

	var isAutoScrollSmartSearcherOpened = false ;

	function f_smartSearchForm() {
	    isAutoScrollSmartSearcherOpened = true ;
	    jQuery("#f_divSmartFinder").show() ;
	    jQuery("#f_smartSearcherOpenImg").hide() ;
	    jQuery("#f_smartSearcherCloseImg").show() ;
	    jQuery("#f_smartSearcherContainer").animate({ height : jQuery("#f_divSmartFinder").height() + 8 }, 280)
	                                                                     .animate({ height : jQuery("#f_divSmartFinder").height() }, 240) ;
	    
	    //(자동스크롤된 스마트검색)left 스마트검색으로 열었을때 left 이미지 감추기 By J.H.S 2013.11.26                                                                 
	    $(".sfinder_btn_left").hide();
	}

	function f_smartSearcherClose() {
	        isAutoScrollSmartSearcherOpened = false ;
	        //(자동스크롤된 스마트검색) 스마트검색 닫을때 left 이미지 보이기 By J.H.S 2013.11.26                                                        
	        $(".sfinder_btn_left").show();
	        jQuery("#f_smartSearcherContainer").animate({ height : jQuery("#f_divSmartFinder").height() + 8 }, 270)
	                                           .animate({ height : 0 } ,240
	                                               , function() {
	                                                      jQuery("#f_divSmartFinder").hide() ;
	                                                      jQuery("#f_smartSearcherCloseImg").hide() ;
	                                                      jQuery("#f_smartSearcherOpenImg").show() ;
	                                                  });
	        //(자동스크롤된 스마트검색) 스마트검색 닫을때 left 이미지 보이기 By J.H.S 2013.11.26 
	        $(".sfinder_btn_left").show();
	}

	jQuery("#f_smartSearcherOpenImg").click(
		function(evt) {
			isAutoScrollSmartSearcherOpened = true ;
			jQuery("#f_divSmartFinder").show() ;
			jQuery("#f_smartSearcherOpenImg").hide() ;
			jQuery("#f_smartSearcherCloseImg").show() ;
	                       //(자동스크롤된 스마트검색) 스마트검색으로 열었을때 left 이미지 감추기 By J.H.S 2013.11.26                                                        
	                       $(".sfinder_btn_left").hide();
			jQuery("#f_smartSearcherContainer").animate({ height : jQuery("#f_divSmartFinder").height() + 8 }, 280)
											 .animate({ height : jQuery("#f_divSmartFinder").height() }, 240) ;
	});

	jQuery("#f_smartSearcherCloseImg").click(
		function (evt) {
			isAutoScrollSmartSearcherOpened = false ;
	                       //(자동스크롤된 스마트검색) 스마트검색 닫을때 left 이미지 보이기 By J.H.S 2013.11.26                                                        
	           $(".sfinder_btn_left").show();
			jQuery("#f_smartSearcherContainer").animate({ height : jQuery("#f_divSmartFinder").height() + 8 }, 270)
											   .animate({ height : 0 } ,240
													, function() {
														jQuery("#f_divSmartFinder").hide();
														jQuery("#f_smartSearcherCloseImg").hide();
														jQuery("#f_smartSearcherOpenImg").show();
													});
	});

	var isScrollingSmartSearcherVisibility = false;
	var scrollSmartTop = 0;
	var scrollSmartSearcherRollingId = null;
	var scrollMovingStep = 0;
	
	function printingScrollSmartSearcher() {
	
		if (autoScrollingSmartSearchWindowReadyId) {
			window.clearTimeout(autoScrollingSmartSearchWindowReadyId) ;
			autoScrollingSmartSearchWindowReadyId = null ;
		}
	
		isScrollingSmartSearcherVisibility = true ;
	
		if (scrollSmartSearcherRollingId == null) {
			scrollSmartSearcherRollingId = window.setInterval(printingScrollSmartSearcher, 20) ;
		}
		var newPos = scrollSmartTop - jQuery("#body").offset().top - (parseInt(jQuery("#f_smart_finder").height()) - scrollMovingStep++) ;
	
		if (newPos >= scrollSmartTop - jQuery("#body").offset().top) {
			jQuery("#f_smart_finder").css({"top":(scrollSmartTop - jQuery("#body").offset().top)}) ;
			window.clearInterval(scrollSmartSearcherRollingId) ;
			scrollSmartSearcherRollingId = null ;
			scrollMovingStep = 0 ;
		} else {
			jQuery("#f_smart_finder").css({"top":newPos}) ;
		}
	}
</script>

<style type="text/css">
#smartSearcherContainer { position : relative ; height : 0 ; background : #FFF ; overflow : hidden ; }
#divSmartFinder { position : absolute ; bottom : 0 ; }
#smartSearchOpenBtn { cursor : pointer ; }
#smartSearcherOpenImg { }
#smartSearcherCloseImg { display : none ; }
.Cscroll_stop img { cursor : pointer ; }
#btnAutoScrollOn { display : none ; }
</style>

<section id="smart_finder">
	<form id="smartSearchFrm" name="SearchItemForm" method="post" onSubmit="" action="/kportal/search/total_search.do" >
		<!-- 스마트 파인더, 고급검색 오픈 -->
		<div id="smartSearcherContainer">
			<div id="divSmartFinder" class="detail_smart higher_search" >
				<div class="helpme_info"><em class="point02 txt_bold">통합검색 키워드입력창</em> 입니다. 검색할 단어를 입력해 주세요.</div>
				<div class="code_search">
					<span><label for="searchInclude" class="txt_bold">반드시포함</label> <input name="searchInclude" id="searchInclude" type="text" value="" class="input_small"/></span>
					<span><label for="searchExcept" class="txt_bold">제외단어</label> <input name="searchExcept" id="searchExcept" type="text" value="" class="input_small"/></span>
					<!--span class="code_check"><input name="searchCode" id="searchCode" type="checkbox" value="0" /> <label for="searchCode">코드검색</label></span-->
				</div>
				<p class="code_search_info"><span class="display_block">원하는 검색결과에 맞춰 키워드를 입력하시면 됩니다. (입력창 모두를 입력하실 필요는 없습니다.)</span>
					<!--코드검색을 선택하시면 한영/영한 번역검색이 불가능합니다.--></p>                                
				<div class="btn_area">
					<!--<img src="/kportal/images/button/btn_helpme.gif" alt="검색정보입력도우미"/>-->
					<button title="검색하기" type="submit"><img src="/kportal/images/button/btn_search.gif" alt="검색하기"/></button></div>
                                <div class="tip_help"><img src="/kportal/images/common/kportal_search1.png" alt="권리별 스마트 검색에서는 보다 자세한 검색을 제공합니다."> </div>
			</div>
		</div>
		<!-- //스마트 파인더, 고급검색 오픈 -->
		<!-- 스마트 파인더, 고급검색 기본 -->
		<div id="divSmartFinderBtn" class="sfinder_open">
	        <span class="sfinder_btn_left">
            <a id="btnToggleSmartFinder2_1" href="javascript:openSmartSearchForm()">
            	<img id="ToggleSmartFinder2_1" src="/kportal/images/common/btn_smartfinder_open_left.gif" alt="항목별 검색을 위해 이곳을 클릭해주세요."/>
            </a>
	        </span>
			<span id="smartSearchOpenBtn" class="sfinder_txt"><a href="javascript:openSmartSearchForm()" id="smartSearcherOpenImg" title="스마트검색 열기 ▼"><img src="/kportal/images/common/btn_smartfinder_open_m.gif" alt="항목별 검색을 위해 이곳을 클릭해주세요."/></a>
			<a href="javascript:hideSearchOption()" id="smartSearcherCloseImg" title="스마트검색 닫기 ▲"><img id="btn_smartfinder_close_higher" src="/kportal/images/common/btn_smartfinder_close.gif" alt="스마트검색 닫기 ▲"/></a></span>
			<span class="Cscroll_stop">
				<a href="javascript:autoScrollSmartSearch(true)" id="btnAutoScrollOn" title="자동스크롤 켜기"><img src="/kportal/images/common/txt_Cscroll_play.gif" alt="자동스크롤 켜기" /></a>
				<a href="javascript:autoScrollSmartSearch(false)" id="btnAutoScrollOff" title="자동스크롤 끄기"><img src="/kportal/images/common/txt_Cscroll_stop.gif" alt="자동스크롤 끄기" /></a>
			</span>
		</div>
		<!-- //스마트 파인더, 고급검색 기본 -->
	</form>
</section>
<script type="text/javascript">
	
	function openSmartSearchForm() {
		isOptionOpened = true;
		jQuery("#divSmartFinder").show();
		jQuery("#smartSearcherOpenImg").hide();
		jQuery("#smartSearcherCloseImg").show();
		jQuery("#smartSearcherContainer").animate({ height : jQuery("#divSmartFinder").height() + 8 }, 280)
										 .animate({ height : jQuery("#divSmartFinder").height() }, 240);	    
	    $(".sfinder_btn_left").hide(); //스마트검색 이미지 변경에 따라 스마트검색창을 열고 닫을 때 스마트검색 왼쪽버튼 표시 상태 변경함. by lhy 2013.08.06
	    jQuery("#searchInclude", jQuery("#divSmartFinder")).focus();
	}
	
	function hideSearchOption() {
		isOptionOpened = false ;
		jQuery("#smartSearcherContainer").animate({ height : jQuery("#divSmartFinder").height() + 8 }, 270)
										 .animate({ height : 0 } ,240
											, function() {
												jQuery("#divSmartFinder").hide() ;
												jQuery("#smartSearcherCloseImg").hide() ;
												jQuery("#smartSearcherOpenImg").show() ;
											} ) ;
		                                                                                             
         //스마트검색 이미지 변경에 따라 스마트검색창을 열고 닫을 때 스마트검색 왼쪽버튼 표시 상태 변경함. by lhy 2013.08.06
         $(".sfinder_btn_left").show();
	}
	
	//var isAutoScrollingSmartSearcher = false ; //By J.H.S 20131014 자동스크롤 켜기로 defalut 함에따라 상태값 true로 변경
	var isAutoScrollingSmartSearcher = true ;
	
	function autoScrollSmartSearch(isScroll) {
		if (isScroll) {
			isAutoScrollingSmartSearcher = true ;
			jQuery("#btnAutoScrollOn").hide() ;
			jQuery("#btnAutoScrollOff").show() ;
		} else {
			isAutoScrollingSmartSearcher = false ;
			jQuery("#btnAutoScrollOff").hide() ;
			jQuery("#btnAutoScrollOn").show() ;
			if (isScrollingSmartSearcherVisibility) {
				hideFlowingSmartForm() ;
			}
		}
	}
	
	function smartSearchSubmission() {
		var searchInclude = jQuery("#searchInclude").val() ;
		var searchExcept = jQuery("#searchExcept").val() ;
		var strstat = "";
		strstat += (searchInclude == "" || searchInclude == null) ? "" : "INC";
		strstat += (searchExcept == "" || searchExcept == null) ? "" : (strstat == "" ? "EXC" : "|EXC");
	
		if (searchInclude.indexOf('!') != -1 && (searchInclude.indexOf(' ') == -1 && searchInclude.indexOf('*') == -1)) {
			throw("<NOT> 연산자 '!'은 <and> 연산자 '*' 와 함께 쓰셔야합니다.") ;
		}
	        
		if (checkSpecialChar(searchInclude)) {
			searchInclude = DelSpecialChar(searchInclude) ;
			if (checkSpecialChar(searchExcept)) {
				searchExcept = DelSpecialChar(searchExcept) ;
				if (searchInclude == "") {
					document.getElementById("searchInclude").focus() ;
					throw("검색어를 입력해 주십시요.") ;
				}
				if (searchExcept.indexOf("+") != -1 || searchExcept.indexOf("!") != -1 || searchExcept.indexOf("?") != -1) {
					document.getElementById("searchExcept").focus() ;
					throw("제외검색어 입력에서는 연산자 '!' , '+' , '?'는 사용할수 없습니다.") ;
				}
				
				var query = "" ;
				var istartcut = 0 ;
				var cutchar = null ;
				var boolcut = false ;
	
				for (var i = 0 ; i < searchExcept.length ; i++) {
					cutchar = searchExcept.charAt(i) ;
					switch (cutchar) {
						case ' ' :
						case '*' :
							query = searchExcept.substring(0, i) ;
							istartcut = i ;
							searchExcept = searchExcept.substring(i + 1, searchExcept.length) ;
							i = 0 ;
							searchInclude = searchInclude + "*!" + query ;
							boolcut = true ;
							break ;
						default :
							query = searchExcept ;
							break ;
					}
				}
	
				if (query.length > 0) {
					/* if (jQuery("#searchCode").prop("checked")) {
						searchInclude = "<WORD>" + searchInclude + "*!" + "<WORD>" + query ;
					} else { */
						searchInclude = searchInclude + "*!" + query ;
					// }
				}
	
				totalSearchCount = 0 ;
			 	resetSearchCountingBoard() ;
	
				jQuery("#searchKeyword").val(searchInclude) ;
				jQuery("#searchQueryInput").val(searchInclude) ;
				jQuery("#searchError").hide() ;
				jQuery("#resultQuery").val(searchInclude) ;
				jQuery("#resultExpression").val(searchInclude) ;
				jQuery("#resultExtends").val("N") ;
				jQuery("#resultSearchInTransKorToEng").val("N") ;
				jQuery("#resultSearchInTransEngToKor").val("N") ;
				jQuery('#strstat').val("SMART|" + strstat);
	             
	            //By J.H.S 20140807 스마트검색시 검색히스토리에 남김 추가.
	            //웹취약점 조치를 위해 < , > 문자 제거 
	            appendSearchKeywordHistory(KIPRIS_TOTAL_HISTORY_KEY, searchInclude.replace(/</gi,"").replace(/>/,""), 10) ;
	            setSearchKeywordHistoryBoard() ;
	            //스마트검색시 최종검색어를 beforeExpression 저장하고 검색결과 내 재검색시 작동하기위해 저장함.
	            jQuery("#beforeExpression").val(searchInclude) ;
				
	            var searchInclude = encodeURL(searchInclude);                   
				getPatentSearchResult(searchInclude, searchInclude) ;
				getDesignSearchResult(searchInclude, searchInclude) ;
				getTrademarkSearchResult(searchInclude, searchInclude) ;
				getFrnUSSearchResult(searchInclude, searchInclude) ;
				getFrnEUSearchResult(searchInclude, searchInclude) ;
				//getFrnPCTSearchResult(searchInclude, searchInclude) ;
				getFrnJPSearchResult(searchInclude, searchInclude) ;
				//getFrnCNSearchResult(searchInclude, searchInclude) ;
				//getFrnENSearchResult(searchInclude, searchInclude) ;
				//getFrnDESearchResult(searchInclude, searchInclude) ;
				//getFrnFRSearchResult(searchInclude, searchInclude) ;
				//getFrnAUSearchResult(searchInclude, searchInclude) ;
				//getFrnCASearchResult(searchInclude, searchInclude) ;
				//getFrnRUSearchResult(searchInclude, searchInclude) ;
				//getFrnTWSearchResult(searchInclude, searchInclude) ;
	                        
	            // NDSL 논문, 저널 추가                        
	            getNdslArticleSearchResult(searchInclude, searchInclude) ;
	            getNdslJournalSearchResult(searchInclude, searchInclude) ;
	
	            // IPNAVI 추가
				getIpNaviPrcdnSearchResult(searchInclude, searchInclude) ;
				getIpNaviConflictSearchResult(searchInclude, searchInclude) ;
	                        
	            // TODO
				//getIpnaviGuidebookSearchResult(searchInclude, searchInclude) ;
	                        
			} else {
				document.getElementById("searchExcept").focus() ;
			}
		} else {
			document.getElementById("searchInclude").focus() ;
		}
	}
	
	jQuery("#smartSearchFrm").submit(
			function(evt) {
	            //hideSearchOption();  //주석해제시 스마트창 닫고 검색하게 함.
	            //By J.H.S 20130807 스마트검색의 [검색하기] 버튼 클릭시 검색서비스 안내를 숨기는 것을 추가함.
	            jQuery("#searchIndex").hide() ;  
	            // ******************** //
				evt.preventDefault() ;
				try {
	                smartSearchSubmission() ;
	                //상단 검색 placeholder hidden By J.H.S 20131022 추가
	                //$('#ol_queryTextlabel').css('visibility','hidden');
					isPageError = false ;
				} catch(e) {
					alertTotalSearchException(e) ;
					//printTotalSearchException(e) ;
				}
	});
	
	var isOptionOpened = false ;
	function resetSearchOption() {
		if (isOptionOpened) hideSearchOption() ;
	
		jQuery("#searchInclude").val("") ;
		jQuery("#searchExcept").val("") ;
	    // jQuery("#searchCode").prop("checked", false) ;
	}
	
	var autoScrollingSmartSearchWindowReadyId = null ;
	jQuery(window).scroll(  //스크롤바 제어 부분 (스마트검색)
			function(evt) {
				if (isAutoScrollingSmartSearcher) {
	
					scrollSmartTop = jQuery(document).scrollTop() ;  //현재 스크롤바의 위치값을 나타냄
	
					if (isScrollingSmartSearcherVisibility) {  //스크롤링해서 스마트검색 이미지가 자동스크롤되서 나타났을 때 True됨
						if (scrollSmartTop > jQuery("#body").offset().top + parseInt(jQuery("#smart_finder").height())) {  //현재 스크롤바 위치값 > (jQuery("#body").offset().top : 191) + (parseInt(jQuery("#smart_finder").height()) : 30)
							if (autoScrollingSmartSearchWindowReadyId) {  
							} else {
								if (!scrollSmartSearcherRollingId) {  //!null -> true
									if (isOptionOpened == true){   //스마트검색을 열고 아래로 스크롤링했을때 자동스크롤 스마트검색이 따라오지 않게 hide함.
	                                	jQuery("#f_smart_finder").hide() ;
                                    } else {                         //스마트검색이 닫혀있고 아래로 스크롤링했을때 자동스크롤 스마트검색이 나오게 show함
                                    	jQuery("#f_smart_finder").css({"top":(parseInt(jQuery(document).scrollTop()) - parseInt(jQuery("#body").offset().top))}) ;
                                    	jQuery("#f_smart_finder").show() ;
                                   }
								}
							}
						} else {
							if (autoScrollingSmartSearchWindowReadyId) { 
								window.clearTimeout(autoScrollingSmartSearchWindowReadyId) ;
								autoScrollingSmartSearchWindowReadyId = null ;
								isScrollingSmartSearcherVisibility = false ;
								jQuery("#f_smart_finder").css({"top":"-1000px"}) ;
							} else { 
								isScrollingSmartSearcherVisibility = false ;
								//isAutoScrollSmartSearcherOpened = false ; //무조건 false 세팅하여 주석처리함. (스마트검색의 열고, 닫음의 유무에따라 값의 세팅)
								if (isAutoScrollSmartSearcherOpened) {      //스마트검색 열면 True, 닫혀있으면 False
									jQuery("#f_smart_finder").animate({top: (0 - jQuery("#f_smart_finder").height())}, 240
											, function() {
												isAutoScrollSmartSearcherOpened = false ;
												jQuery("#f_smartSearcherContainer").css({height : 0}) ;
												jQuery("#f_divSmartFinder").hide() ;
												jQuery("#f_smartSearcherCloseImg").hide() ;
												jQuery("#f_smartSearcherOpenImg").show() ;
												jQuery("#f_smart_finder").css({"top":"-1000px"}) ;
											});
	                                        openSmartSearchForm(); //아래로 스크롤링해서 자동스크롤에서 스마트검색열고, 스크롤링을 위로 올리면 스마트검색이 닫히지 않고 열리도록 하게함. 
								} 
	                                                        else {
									jQuery("#f_smart_finder").animate({top: (0 - jQuery("#f_smart_finder").height())}, 300
											, function() {
												jQuery("#f_smartSearcherContainer").css({height : 0}) ;
												jQuery("#f_divSmartFinder").hide() ;
												jQuery("#f_smartSearcherCloseImg").hide() ;
												jQuery("#f_smartSearcherOpenImg").show() ;
												jQuery("#f_smart_finder").css({"top":"-1000px"}) ;
											}
									) ;
								}
							}
	                                    }
					} else {
						if (scrollSmartTop > jQuery("#body").offset().top + parseInt(jQuery("#smart_finder").height())) { //현재 스크롤바 위치값 > (jQuery("#body").offset().top : 191) + (parseInt(jQuery("#smart_finder").height()) : 30)
							if (!isScrollingSmartSearcherVisibility) {
	                                                        if(isOptionOpened == true){ //스마트검색을 열고 아래로 스크롤링했을때 자동스크롤 스마트검색이 따라오지 않게 hide함.
	                                                            jQuery("#f_smart_finder").hide();
	                                                        }
	                                                        else{ //스마트검색이 닫혀있고 아래로 스크롤링했을때 자동스크롤 스마트검색이 나오게 show함
	                                                            jQuery("#f_smart_finder").css({"top":scrollSmartTop - jQuery("#body").offset().top - jQuery("#f_smart_finder").height()}) ;
	                                                            jQuery("#f_smart_finder").show();
	                                                        }
								isScrollingSmartSearcherVisibility = true ;
								//autoScrollingSmartSearchWindowReadyId = window.setTimeout(printingScrollSmartSearcher, 2000) ;
	                                                        autoScrollingSmartSearchWindowReadyId = window.setTimeout(printingScrollSmartSearcher, 0) ; //0초후에 printingScrollSmartSearcher 함수 실행
							}
						}
					}
				} //if 종료
			}//function 종료
	) ;
	
	//$(window).resize(function(){
	//    //창크기 변경 시 이미지 크기도 함께 변경되도록 2015.03.12 jkc
	//    if($(window).width() >=1200){
	//        $(".tip_help img").attr("src","/kportal/images/common/kportal_search.png");
	//    }else{
	//        $(".tip_help img").attr("src","/kportal/images/common/kportal_search_m.png");
	//    }
	//});

</script>

		



<!-- 왼쪽 메뉴 및 검색 -->
<section id="side">
	<!--div class="Lscroll_control"><img src="/kportal/images/common/txt_Lscroll_stop.gif" alt="메뉴자동스크롤 끄기"/></div-->
	<nav id="snavigation">
		<h2 class="title_hidden">search</h2>
		<ul>
            <li class="menu01"><a href="/kportal/search/total_search.do"><img src="/kportal/images/navigation/sub/menu01_on.gif"  alt="통합검색" /></a></li>
			<li><a href="https://www.kipris.or.kr/kpat/searchLogina.do?next=MainSearch"><img src="/kportal/images/navigation/sub/menu02.gif" alt="특허 &middot;실용신안" /></a></li>
			<li><a href="https://www.kipris.or.kr/kdtj/searchLogina.do?method=loginDG"><img src="/kportal/images/navigation/sub/menu03.gif" alt="디자인" /></a></li>
			<li><a href="https://www.kipris.or.kr/kdtj/searchLogina.do?method=loginTM"><img src="/kportal/images/navigation/sub/menu04.gif" alt="상표" /></a></li>
			<li><a href="https://www.kipris.or.kr/kdtj/searchLogina.do?method=loginJM"><img src="/kportal/images/navigation/sub/menu05.gif" alt="심판" /></a></li>
			<li><a href="https://www.kipris.or.kr/kpa/search/search_kpa.do" target="_blank" title="한국특허영문초록(KPA) 새창으로 열림"><img src="/kportal/images/navigation/sub/menu06.gif" alt="한국특허영문초록(KPA)" /></a></li>
			<li><a href="https://www.kipris.or.kr/abpat/searchLogina.do?next=MainSearch"><img src="/kportal/images/navigation/sub/menu07.gif" alt="해외특허" /></a></li>
			<li><a href="https://www.kipris.or.kr/abtm/search/resultList.jsp"><img src="/kportal/images/navigation/sub/menu08.gif" alt="해외상표" /></a></li>
                        <li><a href="https://www.kipris.or.kr/abdg/searchLogina.do?next=MainSearch"><img src="/kportal/images/navigation/sub/menu10.gif"  alt="해외디자인" /></a></li>
			<li><a href="https://www.kipris.or.kr/kpat/searchLogina.do?next=CyberSearch"><img src="/kportal/images/navigation/sub/menu09.gif" alt="인터넷기술공지" /></a></li>
                        <li><a href="https://www.kipris.or.kr/kpat/searchLogina.do?next=ContestSearch"><img src="/kportal/images/navigation/sub/menu11.gif" alt="아이디어공모전" /></a></li>
                        <li><a href="http://www.kipris.or.kr/kdc/searchLogina.do?next=MainSearch"><img src="/kportal/images/navigation/sub/menu12.gif" alt="문장검색" /></a></li>
		</ul>
	</nav>
	<div class="side_qmenu">
		<h2><img src="/kportal/images/qlink/title_kiprisInfo.gif" alt="KIPRIS 검색이 처음이세요?" /></h2>
		<p><img src="/kportal/images/qlink/txt_kiprisInfo.gif" alt="초보자 GUIDE 페이지로 이동합니다. 검색을 편리하고 유용하게 이용하기 위한 설명을 담았습니다." /></p>
		<p class="qmenu_btn"><a href="http://www.kipris.or.kr/khome/guideMaina.do"><img src="/kportal/images/qlink/btn_search_guide.gif" alt="초보자검색" /></a><a href="http://www.kipris.or.kr/khome/guide/easy/easy_potal.jsp"><img src="/kportal/images/qlink/btn_movie.gif" alt="동영상매뉴얼" /></a></p>
		<article class="link_site">
			<h2><img src="/kportal/images/qlink/title_guresite.gif" alt="관련사이트 새창으로 열림" /></h2>
			<ul class="sitelink">
      <li> <span>
        <label for="patentHomeSiteList">국내 특허 검색사이트</label>
        </span>
        <select id="patentHomeSiteList" name="relationSite1">
            <optgroup label="특허">
                <option value="http://plus.kipris.or.kr">KIPRIS PLUS</option>
<!--            <option value="http://www.kipi.or.kr/ipis">IPIS 지식재산통합검색</option> -->
                <option value="http://biz.kista.re.kr/patentmap/front/common.do?method=main">E-특허나라 </option>
                <option value="http://www.ip-navi.or.kr">국제지재권 분쟁정보 포털</option>
                <option value="http://www.designmap.or.kr">DESIGNMAP</option>
            </optgroup>
            <optgroup label="비특허">
                <option value="http://www.ndsl.kr">Science ON</option>
                <option value="http://www.koreantk.com">한국전통지식포탈</option>
            </optgroup>
        </select>
        <span class="sitelink_go">
        <button id="patentHomeSiteGoBtn" type="button" title="새창으로 열림">go</button>
        </span> </li>
      <li> <span>
        <label for="patentForeignSiteList">해외 특허 검색사이트</label>
        </span>
        <select id="patentForeignSiteList" name="relationSite2">
          <optgroup label="세계지적재산권기구(WIPO)">
          <option value="http://www.wipo.int/pctdb/en/">국제 특허 검색(WIPO)</option>
          <option value="https://www3.wipo.int/branddb/en/">국제 상표 검색</option>
          <option value="http://www.wipo.int/designdb/hague/en/">국제 디자인 검색</option>
          </optgroup>
          <optgroup label="미국특허청(USPTO)">
          <option value="http://www.uspto.gov/patft/index.html">특허검색</option>
          <option value="http://www.uspto.gov/main/trademarks.htm">상표 검색</option>
          </optgroup>
          <optgroup label="유럽특허청(EPO)">
          <option value="https://www.epo.org/searching-for-patents.html">특허 검색</option>
          </optgroup>
          <optgroup label="유럽상표청(EUIPO)">
          <option value="http://www.tmview.org/">상표 검색 </option>
          <option value="https://www.tmdn.org/tmdsview-web/#/dsview">디자인 검색</option>
          </optgroup>
          <optgroup label="일본특허청(J-PlatPat)">
          <option value="https://www.j-platpat.inpit.go.jp/p0000">특허 검색</option>
          <option value="https://www.j-platpat.inpit.go.jp/d0000">디자인 검색</option>
          <option value="https://www.j-platpat.inpit.go.jp/t0000">상표 검색</option>
          </optgroup>
          <optgroup label="호주 특허청">
          <option value="http://www.ic.gc.ca/opic-cipo/cpd/eng/introduction.html">특허 검색</option>
          <option value="http://pericles.ipaustralia.gov.au/atmoss/falcon.application_start">상표 검색</option>
          <option value="http://pericles.ipaustralia.gov.au/adds2/adds.adds_simple_search.paint_simple_search">디자인 검색</option>
          </optgroup>
          <optgroup label="캐나다 특허청">
          <option value="http://www.ic.gc.ca/opic-cipo/cpd/eng/introduction.html">특허 검색</option>
          <option value="https://ised-isde.canada.ca/cipo/trademark-search/srch">상표 검색</option>
          <option value="http://strategis.ic.gc.ca/app/cipo/id/displaySearch.do?language=eng">디자인 검색</option>
          </optgroup>
          <optgroup label="중국 특허청">
          <option value="https://pss-system.cponline.cnipa.gov.cn/conventionalSearchEn">특허 검색</option>
          <option value="http://wcjs.sbj.cnipa.gov.cn/txnT01.do">상표 검색</option>
          </optgroup>
          <optgroup label="덴마크 특허청">
          <option value="http://onlineweb.dkpto.dk/pvsonline/Patent">특허 검색</option>
          <option value="http://onlineweb.dkpto.dk/pvsonline/Varemaerke">상표 검색</option>
          <option value="http://onlineweb.dkpto.dk/pvsonline/Design">디자인 검색</option>
          </optgroup>
          <optgroup label="홍콩">
          <option value="http://ipsearch.ipd.gov.hk/patent/main.jsp?LANG=en">특허 검색</option>
          <option value="http://ipsearch.ipd.gov.hk/trademark/jsp/main.jsp">상표 검색</option>
          </optgroup>
          <optgroup label="영국 특허청">
          <option value="http://www.ipo.gov.uk/types/patent/p-os/p-find/p-ipsum.htm">특허 검색</option>
          <option value="https://www.gov.uk/search-for-trademark">상표 검색</option>
          <option value="http://www.ipo.gov.uk/types/design/d-os/d-find/d-find-number.htm">디자인 검색</option>
          </optgroup>
          <optgroup label="독일 특허청">
          <option value="https://register.dpma.de/DPMAregister/pat/uebersicht">특허 검색</option>
          <option value="https://register.dpma.de/DPMAregister/marke/uebersicht">상표 검색</option>
          <option value="https://register.dpma.de/DPMAregister/gsm/uebersicht">디자인 검색</option>
          </optgroup>
          <optgroup label="뉴질랜드 특허청">
          <option value="https://www.iponz.govt.nz/manage-ip">특허 검색</option>
          <option value="https://www.iponz.govt.nz/manage-ip">상표 검색</option>
          <option value="https://www.iponz.govt.nz/manage-ip">디자인 검색</option>
          </optgroup>
          <optgroup label="필리핀 특허청">
          <option value="https://wipopublish.ipophil.gov.ph/wopublish-search/public/patents">특허 검색</option>
          <option value="http://www.wipo.int/branddb/ph/en/">상표 검색</option>
          </optgroup>
          <optgroup label="러시아 특허청">
         	<option value="https://www.fips.ru/publication-web/publications/IZPM?inputSelectOIS=Invention,UtilityModel&tab=IZPM&searchSortSelect=dtPublish&searchSortDirection=true">특허 검색</option>
			<option value="https://www.fips.ru/publication-web/publications/PO?inputSelectOIS=IndustrialDesign&tab=PO&searchSortSelect=dtPublish&searchSortDirection=true">상표 검색</option>
			<option value="https://www.fips.ru/publication-web/publications/UsrTM?inputSelectOIS=TM,CKTM,AOG,ERAOG,TMIR&tab=UsrTM&searchSortSelect=dtPublish&searchSortDirection=true">디자인 검색</option>
          </optgroup>
          <optgroup label="Questel">
          <option value="https://intelligence.orbit.com/">Orbit</option>
          </optgroup>
        </select>
        <span class="sitelink_go">
        <button id="patentForeignSiteGoBtn" type="button" title="새창으로 열림">go</button>
        </span> </li>
      <li> <span>
        <label for="patentCountrySiteList">각국특허청 사이트</label>
        </span>
        <select id="patentCountrySiteList" name="relationSite3">
          <option value="http://www.kipo.go.kr">한국 지식재산처</option>
          <option value="http://www.wipo.int">세계지적재산권기구 (WIPO)</option>
          <option value="http://www.uspto.gov/">미국 특허상표청 (USPTO)</option>
          <option value="http://www.epo.org/">유럽 특허청 (EPO)</option>
          <option value="http://www.jpo.go.jp/">일본 특허청 (JPO)</option>
          <option value="http://www.dkpto.dk/">덴마크 특허청 </option>
<!--           <option value="http://www.osim.ro">루마니아 특허청 </option> -->
          <option value="http://www.impi.gob.mx/">멕시코 특허청</option>
          <option value="http://www.ige.ch">스위스 특허청</option>
          <option value="http://www.indprop.gov.sk">슬로바키아 특허청 </option>
          <option value="http://www.ipo.gov.uk">영국 특허청 </option>
          <option value="http://www.ipaustralia.gov.au">호주 특허청 </option>
          <option value="http://www.prh.fi">핀란드 특허청 </option>
          <option value="http://www.deutsches-patentamt.de">독일 특허청 </option>
          <option value="http://www.eco.public.lu">룩셈브루크 특허청</option>
          <option value="http://www.inpi.fr">프랑스 지적재산국 </option>
          <option value="http://www.oepm.es">스페인 특허청 </option>
          <option value="https://www.patentamt.at/">오스트리아 특허청 </option>
          <option value="https://www.cnipa.gov.cn/">중국 특허청 </option>
          <option value="http://www.tipo.gov.tw/ ">대만 특허청 </option>
          <option value="http://www.prv.se">스웨덴 특허청 </option>
          <option value="https://www.sztnh.gov.hu/en">헝가리 특허청 </option>
          <option value="http://www.ipd.gov.hk">홍콩정부 지적재산국 </option>
          <option value="http://strategis.ic.gc.ca ">캐나다 특허청 </option>
        </select>
        <span class="sitelink_go">
        <button id="patentCountrySiteGoBtn" type="button" title="새창으로 열림">go</button>
        </span> </li>
      <li> <span>
        <label for="patentInterSiteList">유관기관 사이트</label>
        </span>
        <select id="patentInterSiteList" name="relationSite4">
          <option value="http://www.kipa.org/kipa/index.jsp">한국발명진흥회</option>
          <option value="http://www2.ripc.org">지역지식재산센터</option>
          <option value="http://www.kasi.org/">한국학교발명협회</option>
          <option value="http://www.inventor.or.kr/">한국여성발명협회</option>
          <option value="http://www.kmsk.or.kr/">한국지식경영학회</option>
          <option value="http://www.patent.or.kr">한국특허학회</option>
          <option value="http://www.ficpi.org/">국제변리사연맹 한국협회</option>
          <option value="http://www.kipla.or.kr/">한국지식재산학회</option>
          <option value="http://www.pcc.or.kr/">공익변리사 특허상담센터</option>
        </select>
        <span class="sitelink_go">
        <button id="patentInterSiteGoBtn" type="button" title="새창으로 열림">go</button>
        </span> </li>
    </ul></article>
	</div>
</section>
<script>
jQuery("#patentHomeSiteGoBtn").click(function() { window.open(jQuery("#patentHomeSiteList").val(), null, null) ; }) ;
jQuery("#patentForeignSiteGoBtn").click(function() { window.open(jQuery("#patentForeignSiteList").val(), null, null) ; }) ;
jQuery("#patentCountrySiteGoBtn").click(function() { window.open(jQuery("#patentCountrySiteList").val(), null, null) ; }) ;
jQuery("#patentInterSiteGoBtn").click(function() { window.open(jQuery("#patentInterSiteList").val(), null, null) ; }) ;
</script>
<script>

jQuery("#searchTotalBtn").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/total_search.do") ;
		document.getElementById("searchResultFrm").submit() ;
	}
) ;
jQuery("#searchPatentBtn").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_patent.do") ;
		document.getElementById("searchResultFrm").submit() ;
	}
) ;
jQuery("#searchDesignBtn").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_design.do") ;
		document.getElementById("searchResultFrm").submit() ;
	}
) ;
jQuery("#searchTrademarkBtn").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_trademark.do") ;
		document.getElementById("searchResultFrm").submit() ;
	}
) ;
jQuery("#searchFrnUSBtn").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_frn_us.do") ;
		document.getElementById("searchResultFrm").submit() ;
	}
) ;
jQuery("#searchFrnEUBtn").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_frn_eu.do") ;
		document.getElementById("searchResultFrm").submit() ;
	}
) ;
jQuery("#searchFrnPCTBtn").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_frn_pct.do") ;
		document.getElementById("searchResultFrm").submit() ;
	}
) ;
jQuery("#searchFrnJPBtn").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_frn_jp.do") ;
		document.getElementById("searchResultFrm").submit() ;
	}
) ;
jQuery("#searchFrnCNBtn").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_frn_cn.do") ;
		document.getElementById("searchResultFrm").submit() ;
	}
) ;
jQuery("#searchFrnENBtn").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_frn_en.do") ;
		document.getElementById("searchResultFrm").submit() ;
	}
) ;
jQuery("#searchFrnDEBtn").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_frn_de.do") ;
		document.getElementById("searchResultFrm").submit() ;
	}
) ;
jQuery("#searchFrnFRBtn").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_frn_fr.do") ;
		document.getElementById("searchResultFrm").submit() ;
	}
) ;
jQuery("#searchFrnAUBtn").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_frn_au.do") ;
		document.getElementById("searchResultFrm").submit() ;
	}
) ;
jQuery("#searchFrnCABtn").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_frn_ca.do") ;
		document.getElementById("searchResultFrm").submit() ;
	}
) ;
jQuery("#searchFrnRUBtn").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_frn_ru.do") ;
		document.getElementById("searchResultFrm").submit() ;
	}
) ;
jQuery("#searchFrnTWBtn").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_frn_tw.do") ;
		document.getElementById("searchResultFrm").submit() ;
	}
) ;
jQuery("#searchNdsl").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_ndsl.do") ;
		jQuery("#searchResultFrm").submit() ;
	}
) ;
jQuery("#searchNdslArticle").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_ndsl.do?category=article") ;
		$('#ndslDisplayCount').val($('#opt28').val());
		$('#ndslCategory').val('');
		jQuery("#searchResultFrm").submit() ;
		return false;
	}
) ;
jQuery("#searchNdslJournal").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_ndsl.do?category=journal") ;
		$('#ndslDisplayCount').val($('#opt28').val());
		$('#ndslCategory').val('');
		jQuery("#searchResultFrm").submit() ;
		return false;
	}
) ;

</script>
<!-- //왼쪽 메뉴 및 검색 -->

		<!-- 콘텐츠 -->
		<section id="content">
			<h1 class="title_hidden">통합검색</h1>
                        
			<!--통합검색 항목-->     
			


<script type="text/javascript">

var totalSearchCount = 0 ;
var totalSearchCountNdsl = 0;
var totalSearchCountIpNavi =0;
var searchingPageClass = "total" ;

function resetSearchCountingBoard() {
	totalSearchCountNdsl = 0;  //By J.H.S 20130828 NDSL 총 카운트수 리셋
	totalSearchCountIpNavi = 0;
	jQuery("#resultCountTotal").html("-") ;
        jQuery("#resultCountIpNavi").html("-") ;
	setPatentSearchResultCount(-1) ;
	setDesignSearchResultCount(-1) ;
	setTrademarkSearchResultCount(-1) ;
	setFrnUSSearchResultCount(-1) ;
	setFrnEUSearchResultCount(-1) ;
	//setFrnPCTSearchResultCount(-1) ;
	setFrnJPSearchResultCount(-1) ;
	//setFrnCNSearchResultCount(-1) ;
	//setFrnENSearchResultCount(-1) ;
	//setFrnDESearchResultCount(-1) ;
	//setFrnFRSearchResultCount(-1) ;
	//setFrnAUSearchResultCount(-1) ;
	//setFrnCASearchResultCount(-1) ;
	//setFrnRUSearchResultCount(-1) ;
	//setFrnTWSearchResultCount(-1) ;
	
        // NDSL 추가
        setNdslArticleSearchResultCount(-1);
        setNdslJournalSearchResultCount(-1);
	
        // IPNAVI 추가
	setIpNaviPrcdnSearchResultCount(-1);
	setIpNaviConflictSearchResultCount(-1);
	//setIpNaviNewsletterSearchResultCount(-1);
	//setIpNaviGuidebookSearchResultCount(-1);
}

function setTotalSearchResultCount() {
	if (totalSearchCount > -1) {
		jQuery("#resultCountTotal").html("<span class=\"letter0\">" + numberFormat(totalSearchCount) + "</span>") ;
	} else {
		jQuery("#resultCountTotal").html("-") ;
	}
}
function setPatentSearchResultCount(N) {
	if (N > -1) {
		totalSearchCount += parseInt(N) ;
		setTotalSearchResultCount() ;
		jQuery("#resultCountPatent").html("<span class=\"letter0\">" + numberFormat(N) + "</span>") ;
	} else {
		jQuery("#resultCountPatent").html("-") ;
	}
}
function setDesignSearchResultCount(N) {
	if (N > -1) {
		totalSearchCount += parseInt(N) ;
		setTotalSearchResultCount() ;
		jQuery("#resultCountDesign").html("<span class=\"letter0\">" + numberFormat(N) + "</span>") ;
	} else {
		jQuery("#resultCountDesign").html("-") ;
	}
}
function setTrademarkSearchResultCount(N) {
	if (N > -1) {
		totalSearchCount += parseInt(N) ;
		setTotalSearchResultCount() ;
		jQuery("#resultCountTrademark").html("<span class=\"letter0\">" + numberFormat(N) + "</span>") ;
	} else {
		jQuery("#resultCountTrademark").html("-") ;
	}
}
//<span class="letter0 point02">23</span>건</span>
//<span class="letter0">23</span>건</span>
function setFrnUSSearchResultCount(N) {
	if (N > -1) {
		totalSearchCount += parseInt(N) ;
		setTotalSearchResultCount() ;
		//if (N > 9999) {
		//	jQuery("#resultCountFrnUS").html("<span class=\"letter0\">" + numberFormat(9999) + "+</span>") ;
		//} else {
			jQuery("#resultCountFrnUS").html("<span class=\"letter0\">" + numberFormat(N) + "</span>") ;
		//}
	} else {
		jQuery("#resultCountFrnUS").text("-") ;
	}
}
function setFrnEUSearchResultCount(N) {
	if (N > -1) {
		totalSearchCount += parseInt(N) ;
		setTotalSearchResultCount() ;
		//if (N > 9999) {
		//	jQuery("#resultCountFrnEU").html("<span class=\"letter0\">" + numberFormat(9999) + "+</span>") ;
		//} else {
			jQuery("#resultCountFrnEU").html("<span class=\"letter0\">" + numberFormat(N) + "</span>") ;
		//}
	} else {
		jQuery("#resultCountFrnEU").text("-") ;
	}
}
//function setFrnPCTSearchResultCount(N) {
//	if (N > -1) {
//		totalSearchCount += parseInt(N) ;
//		setTotalSearchResultCount() ;
//		//if (N > 9999) {
//		//	jQuery("#resultCountFrnPCT").html("<span class=\"letter0\">" + numberFormat(9999) + "+</span>") ;
//		//} else {
//			jQuery("#resultCountFrnPCT").html("<span class=\"letter0\">" + numberFormat(N) + "</span>") ;
//		//}
//	} else {
//		jQuery("#resultCountFrnPCT").text("-") ;
//	}
//}
function setFrnJPSearchResultCount(N) {
	if (N > -1) {
		totalSearchCount += parseInt(N) ;
		setTotalSearchResultCount() ;
		//if (N > 9999) {
		//	jQuery("#resultCountFrnJP").html("<span class=\"letter0\">" + numberFormat(9999) + "+</span>") ;
		//} else {
			jQuery("#resultCountFrnJP").html("<span class=\"letter0\">" + numberFormat(N) + "</span>") ;
		//}
	} else {
		jQuery("#resultCountFrnJP").text("-") ;
	}
}
//function setFrnCNSearchResultCount(N) {
//	if (N > -1) {
//		totalSearchCount += parseInt(N) ;
//		setTotalSearchResultCount() ;
//		//if (N > 9999) {
//		//	jQuery("#resultCountFrnCN").html("<span class=\"letter0\">" + numberFormat(9999) + "+</span>") ;
//		//} else {
//			jQuery("#resultCountFrnCN").html("<span class=\"letter0\">" + numberFormat(N) + "</span>") ;
//		//}
//	} else {
//		jQuery("#resultCountFrnCN").text("-") ;
//	}
//}
//function setFrnENSearchResultCount(N) {
//	if (N > -1) {
//		totalSearchCount += parseInt(N) ;
//		setTotalSearchResultCount() ;
//		//if (N > 9999) {
//		//	jQuery("#resultCountFrnEN").html("<span class=\"letter0\">" + numberFormat(9999) + "+</span>") ;
//		//} else {
//			jQuery("#resultCountFrnEN").html("<span class=\"letter0\">" + numberFormat(N) + "</span>") ;
//		//}
//	} else {
//		jQuery("#resultCountFrnEN").text("-") ;
//	}
//}
//function setFrnDESearchResultCount(N) {
//	if (N > -1) {
//		totalSearchCount += parseInt(N) ;
//		setTotalSearchResultCount() ;
//		//if (N > 9999) {
//		//	jQuery("#resultCountFrnDE").html("<span class=\"letter0\">" + numberFormat(9999) + "+</span>") ;
//		//} else {
//			jQuery("#resultCountFrnDE").html("<span class=\"letter0\">" + numberFormat(N) + "</span>") ;
//		//}
//	} else {
//		jQuery("#resultCountFrnDE").text("-") ;
//	}
//}
//function setFrnFRSearchResultCount(N) {
//	if (N > -1) {
//		totalSearchCount += parseInt(N) ;
//		setTotalSearchResultCount() ;
//		if (searchingPageClass == "frn_fr") {
//			//if (N > 999) {
//			//	jQuery("#resultCountFrnFR").html("<span class=\"letter0\">999+</span>") ;
//			//} else {
//				jQuery("#resultCountFrnFR").html("<span class=\"letter0\">" + numberFormat(N) + "</span>") ;
//			//}
//		} else {
//			//if (N > 9999) {
//			//	jQuery("#resultCountFrnFR").html("<span class=\"letter0\">" + numberFormat(9999) + "+</span>") ;
//			//} else {
//				jQuery("#resultCountFrnFR").html("<span class=\"letter0\">" + numberFormat(N) + "</span>") ;
//			//}
//		}
//	} else {
//		jQuery("#resultCountFrnFR").text("-") ;
//	}
//}
//function setFrnAUSearchResultCount(N) {
//	if (N > -1) {
//		totalSearchCount += parseInt(N) ;
//		setTotalSearchResultCount() ;
//		//if (N > 9999) {
//		//	jQuery("#resultCountFrnAU").html("<span class=\"letter0\">" + numberFormat(9999) + "+</span>") ;
//		//} else {
//			jQuery("#resultCountFrnAU").html("<span class=\"letter0\">" + numberFormat(N) + "</span>") ;
//		//}
//	} else {
//		jQuery("#resultCountFrnAU").text("-") ;
//	}
//}
//function setFrnCASearchResultCount(N) {
//	if (N > -1) {
//		totalSearchCount += parseInt(N) ;
//		setTotalSearchResultCount() ;
//		if (searchingPageClass == "frn_ca") {
//			//if (N > 999) {
//			//	jQuery("#resultCountFrnCA").html("<span class=\"letter0\">999+</span>") ;
//			//} else {
//				jQuery("#resultCountFrnCA").html("<span class=\"letter0\">" + numberFormat(N) + "</span>") ;
//			//}
//		} else {
//			//if (N > 9999) {
//			//	jQuery("#resultCountFrnCA").html("<span class=\"letter0\">" + numberFormat(9999) + "+</span>") ;
//			//} else {
//				jQuery("#resultCountFrnCA").html("<span class=\"letter0\">" + numberFormat(N) + "</span>") ;
//			//}
//		}
//	} else {
//		jQuery("#resultCountFrnCA").text("-") ;
//	}
//}
//function setFrnRUSearchResultCount(N) {
//	if (N > -1) {
//		totalSearchCount += parseInt(N) ;
//		setTotalSearchResultCount() ;
//		if (searchingPageClass == "frn_ru") {
//			//if (N > 999) {
//			//	jQuery("#resultCountFrnRU").html("<span class=\"letter0\">999+</span>") ;
//			//} else {
//				jQuery("#resultCountFrnRU").html("<span class=\"letter0\">" + numberFormat(N) + "</span>") ;
//			//}
//		} else {
//			//if (N > 9999) {
//			//	jQuery("#resultCountFrnRU").html("<span class=\"letter0\">" + numberFormat(9999) + "+</span>") ;
//			//} else {
//				jQuery("#resultCountFrnRU").html("<span class=\"letter0\">" + numberFormat(N) + "</span>") ;
//			//}
//		}
//	} else {
//		jQuery("#resultCountFrnRU").text("-") ;
//	}
//}
//function setFrnTWSearchResultCount(N) {
//	if (N > -1) {
//		totalSearchCount += parseInt(N) ;
//		setTotalSearchResultCount() ;
//		//if (N > 9999) {
//		//	jQuery("#resultCountFrnTW").html("<span class=\"letter0\">" + numberFormat(9999) + "+</span>") ;
//		//} else {
//			jQuery("#resultCountFrnTW").html("<span class=\"letter0\">" + numberFormat(N) + "</span>") ;
//		//}
//	} else {
//		jQuery("#resultCountFrnTW").text("-") ;
//	}
//}

function setNdslArticleSearchResultCount(N){
	if (N > -1) {
		totalSearchCount += parseInt(N) ;
		totalSearchCountNdsl += parseInt(N);
		setTotalSearchResultCount() ;
		setTotalSearchCountNdsl();
		jQuery("#resultCountNdslArticle").html("<span class=\"letter0\">" + numberFormat(N) + "</span>") ;
	} else {
		jQuery("#resultCountNdslArticle").text("-") ;
	}
}
function setNdslJournalSearchResultCount(N){
	if (N > -1) {
		totalSearchCount += parseInt(N) ;
		totalSearchCountNdsl += parseInt(N);
		setTotalSearchResultCount() ;
		setTotalSearchCountNdsl();
		jQuery("#resultCountNdslJournal").html("<span class=\"letter0\">" + numberFormat(N) + "</span>") ;
	} else {
		jQuery("#resultCountNdslJournal").text("-") ;
	}
}

function setTotalSearchCountNdsl() {
	if (totalSearchCountNdsl > -1) {
		jQuery("#resultCountNdsl").html("<span class=\"letter0\">" + numberFormat(totalSearchCountNdsl) + "</span>") ;
	} else {
		jQuery("#resultCountNdsl").html("-") ;
	}
}

function setIpNaviPrcdnSearchResultCount(N) {
	if (N > -1) {
		totalSearchCount += parseInt(N) ;
		setTotalSearchResultCount() ;
		totalSearchCountIpNavi += parseInt(N);
		setTotalSearchCountIpNavi();

		jQuery("#resultCountIpNaviPrcdn").html("<span class=\"letter0\">" + numberFormat(N) + "</span>") ;

	} else {
		jQuery("#resultCountIpNaviPrcdn").text("-") ;
	}
}

function setIpNaviConflictSearchResultCount(N) {
	if (N > -1) {
		totalSearchCount += parseInt(N) ;
		setTotalSearchResultCount() ;
		totalSearchCountIpNavi += parseInt(N);
		setTotalSearchCountIpNavi();
		
		jQuery("#resultCountIpNaviConflict").html("<span class=\"letter0\">" + numberFormat(N) + "</span>") ;

	} else {
		jQuery("#resultCountIpNaviConflict").text("-") ;
	}
}

//function setIpNaviGuidebookSearchResultCount(N) {
//	if (N > -1) {
//		totalSearchCount += parseInt(N) ;
//		setTotalSearchResultCount() ;
//		totalSearchCountIpNavi += parseInt(N);
//		setTotalSearchCountIpNavi();
//		
//		jQuery("#resultCountIpNaviGuidebook").html("<span class=\"letter0\">" + numberFormat(N) + "</span>") ;
//
//	} else {
//		jQuery("#resultCountIpNaviGuidebook").text("-") ;
//	}
//}
//function setIpNaviNewsletterSearchResultCount(N) {
//	if (N > -1) {
//		totalSearchCount += parseInt(N) ;
//		setTotalSearchResultCount() ;
//		totalSearchCountIpNavi += parseInt(N);
//		setTotalSearchCountIpNavi();
//		
//		jQuery("#resultCountIpNaviNewsletter").html("<span class=\"letter0\">" + numberFormat(N) + "</span>") ;
//
//	} else {
//		jQuery("#resultCountIpNaviNewsletter").text("-") ;
//	}
//}

function setTotalSearchCountIpNavi() {
	
	if (totalSearchCountIpNavi > -1) {
		jQuery("#resultCountIpNavi").html("<span class=\"letter0\">" + numberFormat(totalSearchCountIpNavi) + "</span>") ;
	} else {
		jQuery("#resultCountIpNavi").html("-") ;
	}
}

//By J.H.S 20170927 NDSL 안내 DIV 표시
function NdslInfoDivDisplay(){
    var obj = jQuery("#ndslInputExplain");

    if(obj.css("display") == "none"){
     $("#ndslInputExplain").attr('style', 'display:block');
    } else {
     $("#ndslInputExplain").attr('style', 'display:none');
    }
}

</script>
<style type="text/css">
.totalSearch_item_table{
	width:100%;
	border: 0;
	border-spacing: 0;
}
.totalSearch_item_table td{
	padding: 0;
} 
.col_25{
	width : 25%;
}

</style>
<!--통합검색 항목-->            
<div id="totalSearch_item">
<table class="totalSearch_item_table" >
	<caption>통합검색 항목</caption>  
    <colgroup>
        <col class="col_25" />
        <col class="col_25" />
        <col class="col_25" />
        <col class="col_25" />
    </colgroup>
    
    <thead>
    <tr>
     <th scope="row">
         <span class="fl"><img src="/kportal/images/addSearch/itemTitle1.png" alt="국내검색결과"></span>
         <span class="fr"><img src="/kportal/images/addSearch/itemTitle_r1.png" alt="국내검색결과"></span>
     </th>
     <th scope="row">
         <span class="fl"><img src="/kportal/images/addSearch/itemTitle2.png" alt="해외특허"></span>
         <span class="fr"><img src="/kportal/images/addSearch/itemTitle_r1.png" alt="해외검색결과"></span>
     </th>
     <th scope="row">
         <div class="fl" style="width:80px;"><img src="/kportal/images/addSearch/scienceon_logo.png" style="width:100%;" alt="Science ON">
             <a href="javascript:NdslInfoDivDisplay();">
                <img src="/kportal/images/service/questionIcon.gif"  style="vertical-align:-3px;" alt="Science ON 안내문구">
             </a>   
             <div class="inputExplain_layerpopup" >
                 <div class="inputExplain" id="ndslInputExplain" style="padding-top:3px; display:none">
                      <a href="javascript:NdslInfoDivDisplay();"><img  id ="closeBtn" src= "/kportal/images/service/closeBtn.gif" alt="Science ON 안내문구 닫기"></a>
                      <p style="padding-top:15px; font-size:11px;">* Science ON(API) 서비스 제공범위 안내</p>
                      <p style="font-size:11px;letter-spacing: -0.05em;font-weight: 100;">논문: 학위논문을 제외한 국내, 국외 논문을 제공하고 있습니다.</p>
                      <p style="font-size:11px;letter-spacing: -0.05em;font-weight: 100;">저널: 저널, 프로시딩을 제공하고 있습니다.</p>
                      <p style="font-size:11px;letter-spacing: -0.1em;font-weight: 100;">※ 2020년 11월 2일 이후로 NDSL서비스가 Science ON으로 통합되었습니다.</p>
                 </div>  
             </div>
         </div>
         <span class="fr"><a href="http://www.ndsl.kr" target="_blank"><img src="/kportal/images/addSearch/goSite_btn.png" alt="새창열림"></a></span>
     </th>
     <th scope="row">
         <span class="fl"><img src="/kportal/images/addSearch/itemTitle4.png" alt="IP-NAVI"></span>
         <span class="fr"><a href="http://www.ip-navi.or.kr" target="_blank"><img src="/kportal/images/addSearch/goSite_btn.png" alt="새창열림"></a></span>
     </th>
    </tr>
    </thead>
    
    
    <tbody>
    <tr>
    <td>
    	<div class="result_txt r_kr">
        <ul><li  id="searchPatentBtn"><button type="button"><span class="arrow">특허실용:</span><span class="number" id="resultCountPatent">-</span></button></li></ul>
        <ul><li  id="searchDesignBtn"><button type="button"><span class="arrow">디자인:</span><span class="number" id="resultCountDesign">-</span></button></li></ul>
        <ul><li  id="searchTrademarkBtn"><button type="button"><span class="arrow">상표:</span><span class="number" id="resultCountTrademark">-</span></button></li></ul>
        </div>
    </td>
    
    <td>
    	<div class="result_txt r_abpat">
        <ul><li  id="searchFrnUSBtn"><button type="button"><span style="font-size:0.9em;">미국:</span><span class="number" id="resultCountFrnUS">-</span></button></li></ul>
        <ul><li  id="searchFrnEUBtn"><button type="button"><span style="font-size:0.9em;">유럽:</span><span class="number" id="resultCountFrnEU">-</span></button></li></ul>
        
        <ul><li  id="searchFrnJPBtn"><button type="button"><span style="font-size:0.9em;">일본:</span><span class="number" id="resultCountFrnJP">-</span></button></li></ul>
        
        </div>
    </td>
    
    
    
    <td>
    	<div class="result_txt">
        <ul><li  id="searchNdslArticle"><button type="button"><span class="arrow">논문:</span><span class="number" id="resultCountNdslArticle">-</span></button></li></ul>
        <ul><li  id="searchNdslJournal"><button type="button"><span class="arrow">저널:</span><span class="number" id="resultCountNdslJournal">-</span></button></li></ul>
    	<ul><li  id="searchNdsl"><button type="button"><span class="arrow">전체:</span><span class="number" id="resultCountNdsl">-</span></button></li></ul>
        </div>
    </td>
    <td>
    	<div class="result_txt">
        <ul><li  id="searchIpNaviPrcdn"><button type="button"><span class="arrow">판례:</span><span class="number" id="resultCountIpNaviPrcdn">-</span></button></li></ul>
        <ul><li  id="searchIpNaviConflict"><button type="button"><span class="arrow">분쟁:</span><span class="number" id="resultCountIpNaviConflict">-</span></button></li></ul>
    	<ul><li  id="searchIpNavi"><button type="button"><span class="arrow">전체:</span><span class="number" id="resultCountIpNavi">-</span></button></li></ul>
        <!--  
        <ul><li  id="searchIpNaviNewsletter"><button type="button"><span class="arrow">뉴스레터:</span><span class="number" id="resultCountIpNaviNewsletter">-</span></button></li></ul>
        -->
        <!-- TODO
        <ul><li  id="searchIpNaviGuidebook"><button type="button"><span class="arrow">가이드북:</span><span class="number" id="resultCountIpNaviGuidebook">-</span></button></li></ul>
        -->
        </div>
    </td>
    </tr>
    
    <tr>
        <th colspan="4" scope="row">
            <div class="result_txt2">
            <ul><li id="searchTotalBtn"><button type="button"><span>전체검색 결과:</span><span class="number" id="resultCountTotal">-</span></button></li></ul>
            </div>
        </th>
    </tr>
    </tbody>                
</table>
</div>
            
<script>
jQuery("#searchTotalBtn").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/total_search.do") ;
		$('#resultPageClass').val('total');
		document.getElementById("searchResultFrm").submit() ;
	}
) ;
jQuery("#searchPatentBtn").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_patent.do") ;
		document.getElementById("searchResultFrm").submit() ;
	}
) ;
jQuery("#searchDesignBtn").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_design.do") ;
		document.getElementById("searchResultFrm").submit() ;
	}
) ;
jQuery("#searchTrademarkBtn").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_trademark.do") ;
		document.getElementById("searchResultFrm").submit() ;
	}
) ;
jQuery("#searchFrnUSBtn").click(function() {
                jQuery("#searchResultFrm").prop("action", "/kportal/search/search_frn_us.do") ;
		document.getElementById("searchResultFrm").submit() ;
	}
) ;
jQuery("#searchFrnEUBtn").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_frn_eu.do") ;
		document.getElementById("searchResultFrm").submit() ;
	}
) ;
//jQuery("#searchFrnPCTBtn").click(function() {
//		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_frn_pct.do") ;
//		document.getElementById("searchResultFrm").submit() ;
//	}
//) ;
jQuery("#searchFrnJPBtn").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_frn_jp.do") ;
		document.getElementById("searchResultFrm").submit() ;
	}
) ;
/*
jQuery("#searchFrnCNBtn").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_frn_cn.do") ;
		document.getElementById("searchResultFrm").submit() ;
	}
) ;*/
//jQuery("#searchFrnENBtn").click(function() {
//		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_frn_en.do") ;
//		document.getElementById("searchResultFrm").submit() ;
//	}
//) ;
//jQuery("#searchFrnDEBtn").click(function() {
//		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_frn_de.do") ;
//		document.getElementById("searchResultFrm").submit() ;
//	}
//) ;
//jQuery("#searchFrnFRBtn").click(function() {
//		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_frn_fr.do") ;
//		document.getElementById("searchResultFrm").submit() ;
//	}
//) ;
//jQuery("#searchFrnAUBtn").click(function() {
//		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_frn_au.do") ;
//		document.getElementById("searchResultFrm").submit() ;
//	}
//) ;
//jQuery("#searchFrnCABtn").click(function() {
//		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_frn_ca.do") ;
//		document.getElementById("searchResultFrm").submit() ;
//	}
//) ;
//jQuery("#searchFrnRUBtn").click(function() {
//		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_frn_ru.do") ;
//		document.getElementById("searchResultFrm").submit() ;
//	}
//) ;
//jQuery("#searchFrnTWBtn").click(function() {
//		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_frn_tw.do") ;
//		document.getElementById("searchResultFrm").submit() ;
//	}
//) ;
jQuery("#searchNdsl").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_ndsl.do") ;
		jQuery("#searchResultFrm").submit() ;
	}
) ;
jQuery("#searchNdslArticle").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_ndsl.do?category=article") ;
		$('#ndslDisplayCount').val($('#opt28').val());
		$('#ndslCategory').val('');
		jQuery("#searchResultFrm").submit() ;
		return false;
	}
) ;
jQuery("#searchNdslJournal").click(function() {
		jQuery("#searchResultFrm").prop("action", "/kportal/search/search_ndsl.do?category=journal") ;
		$('#ndslDisplayCount').val($('#opt28').val());
		$('#ndslCategory').val('');
		jQuery("#searchResultFrm").submit() ;
		return false;
	}
) ;
jQuery("#searchIpNavi").click(function() {
	jQuery("#searchResultFrm").prop("action", "/kportal/search/search_ipnavi_all.do") ;
	//$('#next').val('listPrcdn');
	jQuery("#searchResultFrm").submit() ;
        }
) ;
jQuery("#searchIpNaviPrcdn").click(function() {
	jQuery("#searchResultFrm").prop("action", "/kportal/search/search_ipnavi_prcdn.do") ;
	//$('#next').val('listPrcdn');
	jQuery("#searchResultFrm").submit() ;
        }
) ;
jQuery("#searchIpNaviConflict").click(function() {
	jQuery("#searchResultFrm").prop("action", "/kportal/search/search_ipnavi_conflict.do") ;
	//$('#next').val('listConflict');
	jQuery("#searchResultFrm").submit() ;
}
) ;
//jQuery("#searchIpNaviNewsletter").click(function() {
//	jQuery("#searchResultFrm").prop("action", "/kportal/search/search_ipnavi_newsletter.do") ;
//	//$('#next').val('listNewsletter');
//	jQuery("#searchResultFrm").submit() ;
//}
//) ;
//jQuery("#searchIpNaviGuidebook").click(function() {
//	jQuery("#searchResultFrm").prop("action", "/kportal/search/search_ipnavi_guidebook.do") ;
//	//$('#next').val('listGuidebook');
//	jQuery("#searchResultFrm").submit() ;
//}
//) ;
</script>
<!--//통합검색 항목-->   

                        <!--//통합검색 항목-->       
            
			<section id="detail_content">
				<!-- 검색결과 보기 type, 엑셀저장, 프린트  -->
				<div class="search_section_head">
					<div class="list_view_type">
						<span id="btnSimpleView" class="img_view_on"><button type="button">이미지보기</button><span class="img_view_txt"></span></span><span id="btnTextView" class="txt_view"><button type="button">요약 함께보기</button><span class="txt_view_txt"></span></span>
					</div>
					<div class=" float_right">
						<span class="icon_print"><a href="javascript:goPrintPreview()">인쇄</a></span>
					</div>
				</div>
				<!-- //검색결과 보기 type, 엑셀저장, 프린트  -->
<script>

var isPageError = false ;

var isSearchExtends = jQuery("#searchInTransCk").prop("checked") ;

var resultViewMode = "IMAGE" ;

jQuery("#btnSimpleView").click(
		function(evt) {
			resultViewMode = "IMAGE" ;
			jQuery("#btnTextView").removeClass().addClass("txt_view") ;
			jQuery(this).removeClass().addClass("img_view_on") ;

			if (!isPageError) {
				changePatentResultViewMode() ;
				changeDesignResultViewMode() ;
				changeTrademarkResultViewMode() ;
				changeFrnUSResultViewMode() ;
				changeFrnEUResultViewMode() ;
				//changeFrnPCTResultViewMode() ;
				changeFrnJPResultViewMode() ;
				//changeFrnCNResultViewMode() ;
				//changeFrnENResultViewMo++++++++de() ;
				//changeFrnDEResultViewMode() ;
				//changeFrnFRResultViewMode() ;
				//changeFrnAUResultViewMode() ;
				//changeFrnCAResultViewMode() ;
				//changeFrnRUResultViewMode() ;
				//changeFrnTWResultViewMode() ;
                                changeIpnaviPrcdnResultViewMode() ;
				changeIpnaviConflictResultViewMode() ;
                                // TODO
				//changeIpnaviGuidebookResultViewMode() ;                                
			}
		}
) ;

jQuery("#btnTextView").click(
		function(evt) {
			resultViewMode = "TEXT" ;
			jQuery("#btnSimpleView").removeClass().addClass("img_view") ;
			jQuery(this).removeClass().addClass("txt_view_on") ;

			if (!isPageError) {
				changePatentResultViewMode() ;
				changeDesignResultViewMode() ;
				changeTrademarkResultViewMode() ;
				changeFrnUSResultViewMode() ;
				changeFrnEUResultViewMode() ;
				//changeFrnPCTResultViewMode() ;
				changeFrnJPResultViewMode() ;
				//changeFrnCNResultViewMode() ;
				//changeFrnENResultViewMode() ;
				//changeFrnDEResultViewMode() ;
				//changeFrnFRResultViewMode() ;
				//changeFrnAUResultViewMode() ;
				//changeFrnCAResultViewMode() ;
				//changeFrnRUResultViewMode() ;
				//changeFrnTWResultViewMode() ;

                                changeIpnaviPrcdnResultViewMode() ;
				changeIpnaviConflictResultViewMode() ;
                                // TODO
				//changeIpnaviGuidebookResultViewMode() ;
			}
		}
) ;

</script>
                                <!-- 구글 통계 관련추가 By J.H.S 20130502 -->
                                <script>
                                    (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
                                    (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
                                    m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
                                    })(window,document,'script','//www.google-analytics.com/analytics.js','ga');
                                    
                                    ga('create', 'UA-40578824-1', 'kipris.or.kr');
                                    ga('send', 'pageview');
                                </script>    
				<!-- //검색서비스 안내  -->
				<article id="searchIndex" class="search_nodata">
					<div class="nodata_info">KIPRIS의 <span class="point02">통합검색</span> 서비스입니다.</div>
					<h2 class="solution_title"><img src="/kportal/images/common/txt_searchTip.gif" alt="통합검색 검색 tip" /></h2>
					<ol class="solution_list">
						<li><span class="num01">1</span> 펼치기 버튼을 눌러 긴 검색식의 경우 자유롭게 입력/편집해보세요.</li>
						<li><span class="num02">2</span> 정확한 검색결과를 원하시면 스마트 검색, 결과 내 재검색, 검색어 확장 기능을 효율적으로 이용해보세요.</li>
						<li><span class="num03">3</span> 특허용어가 어려우시다면 도움말, 용어사전 등을 이용해보세요.</li>
						<li><span class="num04">4</span> 보다 다양한 기능을  이용해보시려면 회원가입을 해보세요.</li>
					</ol>
					<h2 class="solution_title"><img src="/kportal/images/common/txt_searchTip_data.gif" alt="데이터 제공안내 tip" /></h2>
					<div class="solution_list">
						<li><span class="num01">1</span> 특허법 등 관련 법령에 따른 미공개 데이터, 데이터 미입수 또는 과거 데이터 미비 등으로 인한 데이터는 조회되지 않을 수 있습니다.</li>
					</div>
					<div class="solution_action">
						<h3>KIPRIS검색이 처음이신가요?</h3>
						<p><span class="first"><a href="http://www.kipris.or.kr/khome/guideMaina.do">초보자검색</a></span><span><a href="http://www.kipris.or.kr/khome/guide/easy/easy_potal.jsp">동영상메뉴얼</a></span></p>
					</div>
				</article>
				<!-- //검색서비스 안내  -->

				<article id="searchError" class="search_nodata">
					<div id="searchErrorMessage" class="nodata_info"></div>
					<div class="solution_action">
						<h3>검색결과의 문제점을 해결하지 못하셨나요?</h3>
						<p><span class="first"><a href="http://www.kipris.or.kr/khome/kr/qa.do?act=qaF">Q&amp;A</a></span><span><a href="http://www.kipris.or.kr/khome/kr/faq.do?act=list">FAQ</a></span> <span><a href="http://www.kipris.or.kr/khome/guide/guide.jsp">초보자검색</a></span> <span><a href="http://www.kipris.or.kr/khome/kr/sug.do?act=sugF">신고및제안</a></span></p>
					</div>
				</article>


<form name="patentMoreFrm" id="patentMoreFrm" method="post">
				<section id="resultPatent" class="search_section">
					<div id="patentResultLoadingBoard"></div>
					<div id="patentResultLoading"><img src="/kportal/images/common/loading_patent.gif" alt="특허/실용신안 검색결과를 불러오고 있습니다." /></div>
					<h2 id="patentTitle" class="total_title">[특허실용] <button type="submit" id="morePatentResult2" ><span id="patentResultCountBoard"><em class="txt_bold">-</em>건 검색</span></button></h2>
					<div id="patentResultList">
						<div class="search_blank"></div>
					</div>

<input type="hidden" name="next" value="patent" />
<input type="hidden" id="patentQueryText" name="queryText" value="" />
<input type="hidden" id="patentExpression" name="expression" value="" />
<input type="hidden" name="config" value="G1111111111111111SSX11111111111111111" />
<input type="hidden" id="patentSearchInTrans" name="searchInTrans" value="" />
<input type="hidden" name="sortField1" value="Score" />
<input type="hidden" name="sortState1" value="Desc" />
<input type="hidden" name="numPerPage" value="30" />
<input type="hidden" name="currentPage" value="1" />
<input type="hidden" id="highlightKeyword" name="highlightKeyword" value="" />
					<p id="patentResultMore" class="total_more">
						<span class="more"><button type="submit" id="morePatentResult" >통합검색<span style="color:#00a13a"> 더보기</span></button></span>
                                                <span class="more_plus"><button type="submit" id="goPatentResult" >특허실용신안<span style="color:#00a13a"> 더보기</span></button></span>                                            
					</p>
                                </section>
</form>
				
<script type="text/javascript">

function plstdescopen(){
    newPopupWindow('http://www.kipris.or.kr/khome/help/help01/help01_2.jsp#chapter3','HelpWin',820, 800, 'C', 'M', 'scrollbars=yes');
}

jQuery("#morePatentResult").click(
	function(evt) {
		jQuery("#patentMoreFrm").prop("action", "/kportal/search/search_patent.do") ;
	}
) ;      
jQuery("#morePatentResult2").click(
	function(evt) {
		jQuery("#patentMoreFrm").prop("action", "/kportal/search/search_patent.do") ;
	}
) ;
jQuery("#goPatentResult").click(
	function(evt) {
		//jQuery("#totalSearchFrm").prop("action", "https://www.kipris.or.kr/kpat/resulta.do?next=ResultList") ;
                jQuery("#patentMoreFrm").prop("action", "https://www.kipris.or.kr/kpat/searchLogina.do?next=MainSearch&checkPot=Y") ;
	}
) ;

var patentResultXmlData = null ;

function addPatentResult(xml) {

	var articleIdx = 0 ;
	jQuery(xml).find("search").find("articles").find("article").each(
		function(idx) {

			try {

				var TTL = jQuery(this).find("TTL").text() ;
				var TLT = jQuery(this).find("TLT").text() ;
				if (TLT != "") {
					TLT = "(" + TLT + ")" ;
				}

				var newTagStr = "" ;

				if (resultViewMode == "TEXT") {

					newTagStr += '<article>' ;
					newTagStr += '	<div class="search_section_title">' ;
					//newTagStr += '		<span class="float_left"><input type="checkbox" id="search_extend" /></span>' ;
					newTagStr += '		<h1 class="stitle"><a href="javascript:plstdescopen();" title="행정상태 도움말 새창으로 열림"><span class="{LST_CSS}">{LST}</span></a> <a href="{VIEW_LINK}" title="새창으로 열림">{TLV}</a></h1>' ;
					newTagStr += '		<div class="btn_doc">' ;

					if (jQuery(this).find("judgementTextFg").text() == "Y") {
                                                newTagStr += '			<a href="{VIEW_LINK_JUDGEMENT}" title="심판사항 새창으로 열림"><img src="/kportal/images/button/btn_judgment.gif" alt="심판사항" /></a>' ;
                                        }
                                        //if (jQuery(this).find("examinedTextFg").text() == "Y") {
					//	newTagStr += '			<a href="{FULLTEXT_LINK}" title="공보 새창으로 열림"><img src="/kportal/images/button/btn_kor.gif" alt="공보" /></a>' ;
					//}
                                        newTagStr += '				<a href="{SPAT}" title="새창으로 열림"><img src="/kportal/images/button/alikePT.png" alt="유사특허" /></a>' ;
                                        newTagStr += '			<a href="{FULLTEXT_LINK}" title="공보 새창으로 열림"><img src="/kportal/images/button/btn_kor.gif" alt="공보" /></a>' ;

                                        //newTagStr += '			 <a href="{K2E_LINK}" title="K2E 새창으로 열림"><img src="/kportal/images/button/btn_k2e.gif" alt="K2E" /></a>' ;
					newTagStr += '		</div>' ;
					newTagStr += '	</div>' ;
					newTagStr += '	<div class="search_basic_info">' ;
					newTagStr += '		<ul class="noimg_list">' ;
					newTagStr += '			<li class="left_width"><span>IPC :</span> <span class="point01">{IPC}</span></li>' ;
					newTagStr += '			<li class="right_width letter1"><span>출원인 :</span> <font title="{APV}">{APV}</font></li>' ;
					newTagStr += '			<li class="left_width"><span>출원번호 :</span> <a href="{VIEW_LINK}" title="새창으로 열림"><span class="point01">{VdkVgwKey}</span></a></li>' ;
					newTagStr += '			<li class="right_width"><span>출원일자 :</span> {ADV}</li>' ;

                                        if ((jQuery(this).find("GNV").text() == "") || (jQuery(this).find("GNV").text() == " ")) {
                                                newTagStr += '		<li class="left_width"><span>등록번호 :</span></li>' ;
                                        }
					else{
						newTagStr += '		<li class="left_width"><span>등록번호 :</span> <a href="{VIEW_LINK_RGST}" title="새창으로 열림"><span class="point01">{GNV}</span></a></li>' ;
					}
					
                                        newTagStr += '			<li class="right_width"><span>등록일자 :</span> {GDV}</li>' ;
					newTagStr += '			<li class="left_width"><span>공개번호 :</span> {ONV}</li>' ;
					newTagStr += '			<li class="right_width"><span>공개일자 :</span> {ODV}</li>' ;
					newTagStr += '			<li class="txt_deputy"><span>대리인 :</span> <font title="{AGV}">{AGV}</font></li>' ;
					newTagStr += '			<li class="txt_inventor"><span>발명자 :</span> <font title="{INV}">{INV}</font></li>' ;
					newTagStr += '		</ul>' ;
					newTagStr += '		<div class="search_detail_content">' ;
					newTagStr += '			<div class="search_txt">' ;
					newTagStr += '				<span class="btn_abstract"><img src="/kportal/images/button/btn_abstract.gif" alt="요약" /></span>' ;
					newTagStr += '				{ABV}' ;
					newTagStr += '			</div>' ;
					newTagStr += '		</div>' ;
					newTagStr += '	</div>' ;
					newTagStr += '</article>' ;

				} else {

					newTagStr += '<article>' ;
					newTagStr += '	<div class="search_section_title">' ;
					//newTagStr += '		<span class="float_left"><input type="checkbox" id="search_extend" /></span>' ;
					newTagStr += '		<h1 class="stitle"><a href="javascript:plstdescopen();" title="행정상태 도움말 새창으로 열림"><span class="{LST_CSS}">{LST}</span></a> <a href="{VIEW_LINK}" title="새창으로 열림">{TLV}</a></h1>' ;
					newTagStr += '		<div class="btn_doc">' ;

                                        if (jQuery(this).find("judgementTextFg").text() == "Y") {
                                                newTagStr += '			<a href="{VIEW_LINK_JUDGEMENT}" title="심판사항 새창으로 열림"><img src="/kportal/images/button/btn_judgment.gif" alt="심판사항" /></a>' ;
                                        }
					//if (jQuery(this).find("examinedTextFg").text() == "Y") {
					//	newTagStr += '			<a href="{FULLTEXT_LINK}" title="공보 새창으로 열림"><img src="/kportal/images/button/btn_kor.gif" alt="공보" /></a>' ;
					//}
                                        newTagStr += '				<a href="{SPAT}" title="새창으로 열림"><img src="/kportal/images/button/alikePT.png" alt="유사특허" /></a>' ;
                                        newTagStr += '			<a href="{FULLTEXT_LINK}" title="공보 새창으로 열림"><img src="/kportal/images/button/btn_kor.gif" alt="공보" /></a>' ;

					//newTagStr += '			 <a href="{K2E_LINK}" title="K2E 새창으로 열림"><img src="/kportal/images/button/btn_k2e.gif" alt="K2E" /></a>' ;
					newTagStr += '		</div>' ;
					newTagStr += '	</div>' ;
					newTagStr += '	<div class="search_basic_info">' ;
					newTagStr += '		<div class="thumb"><a href="{VIEW_IMAGE_LINK}" title="새창으로 열림"><img src="{IMG_SRC}" width="100" height="100" alt="{IMG_ALT}" /></a></div>' ;
					newTagStr += '		<ul class="search_info_list">' ;
					newTagStr += '			<li class="left_width"><span>IPC :</span> <span class="point01">{IPC}</span></li>' ;
					newTagStr += '			<li class="right_width letter1"><span>출원인 :</span> <font title="{APV}">{APV}</font></li>' ;
					newTagStr += '			<li class="left_width"><span>출원번호 :</span> <a href="{VIEW_LINK}" title="새창으로 열림"><span class="point01">{VdkVgwKey}</span></a></li>' ;
					newTagStr += '			<li class="right_width"><span>출원일자 :</span> {ADV}</li>' ;
					
                                        if ((jQuery(this).find("GNV").text() == "") || (jQuery(this).find("GNV").text() == " ")) {
                                                newTagStr += '		<li class="left_width"><span>등록번호 :</span></li>' ;
                                        }
					else{
						newTagStr += '		<li class="left_width"><span>등록번호 :</span> <a href="{VIEW_LINK_RGST}" title="새창으로 열림"><span class="point01">{GNV}</span></a></li>' ;
					}
                                        
                                        newTagStr += '			<li class="right_width"><span>등록일자 :</span> {GDV}</li>' ;
					newTagStr += '			<li class="left_width"><span>공개번호 :</span> {ONV}</li>' ;
					newTagStr += '			<li class="right_width"><span>공개일자 :</span> {ODV}</li>' ;
					newTagStr += '			<li class="left_width"><span>대리인 :</span> <font title="{AGV}">{AGV}</font></li>' ;
					newTagStr += '			<li class="right_width"><span>발명자 :</span> <font title="{INV}">{INV}</font></li>' ;
					newTagStr += '		</ul>' ;
					newTagStr += '          <div id="btnOpenABVArea{VdkVgwKey}" class="btn_close"><span class="more"><a href="{ABVOPEN}">열기</a></span></div> ' ;
					newTagStr += '		<div id="div_search_detail_{VdkVgwKey}" class="search_detail_content" style="display:none">' ;
					newTagStr += '		        <div class="search_txt">' ;
					newTagStr += '			        <span class="btn_abstract"><img src="/kportal/images/button/btn_abstract.gif" alt="요약"/></span>' ;
					newTagStr += '				<div id="search_txt_kr_{VdkVgwKey}">{ABV}</div>' ;
					newTagStr += '                          <div id="btnCloseABVArea{VdkVgwKey}" class="btn_close"><span class="close"><a href="{ABVCLOSE}">닫기</a></span></div>' ;
                                        newTagStr += '			</div>' ;
					newTagStr += '		</div>' ;
                                        newTagStr += '	</div>' ;
					newTagStr += '</article>' ;

				}

				switch (jQuery(this).find("LST").text()) {
					case "A" :
						newTagStr = newTagStr.replace(/{LST_CSS}/g, "box_small_a") ; break ;
					case "B" :
						newTagStr = newTagStr.replace(/{LST_CSS}/g, "box_small_b") ; break ;
					case "J" :
						newTagStr = newTagStr.replace(/{LST_CSS}/g, "box_small_j") ; break ;
					case "R" :
						newTagStr = newTagStr.replace(/{LST_CSS}/g, "box_small_r") ; break ;
					case "F" :
						newTagStr = newTagStr.replace(/{LST_CSS}/g, "box_small_f") ; break ;
					case "I" :
						newTagStr = newTagStr.replace(/{LST_CSS}/g, "box_small_i") ; break ;
					case "C" :
						newTagStr = newTagStr.replace(/{LST_CSS}/g, "box_small_c") ; break ;
					case "G" :
						newTagStr = newTagStr.replace(/{LST_CSS}/g, "box_small_g") ; break ;
					default :
						newTagStr = newTagStr.replace(/{LST_CSS}/g, "") ; break ;
				}

				var ABV = jQuery(this).find("ABV").text() ;
				if (ABV == "내용 없음" || ABV == "내용없음" || ABV == "내용 없음.") { ABV = "" ; }
				if (ABV == "") {
					ABV = '<span class="no_abstract">내용 없음</span>' ;
				}

                                newTagStr = newTagStr.replace(/{ABVOPEN}/g, "javascript:openABVArea('{VdkVgwKey}', 'open')") ;
                                newTagStr = newTagStr.replace(/{ABVCLOSE}/g, "javascript:openABVArea('{VdkVgwKey}', 'close')") ;

                                newTagStr = newTagStr.replace(/{VIEW_LINK}/g, "javascript:openDetail('{VdkVgwKey}', {ARTICLE_IDX}, '', 'biblio', '30', 'View01')") ;
                                newTagStr = newTagStr.replace(/{SPAT}/g, "javascript:openKDC('{VdkVgwKey}')") ;
                                newTagStr = newTagStr.replace(/{FULLTEXT_LINK}/g, "javascript:openDetail('{VdkVgwKey}', {ARTICLE_IDX}, '', 'fulltext', '30', 'View03')") ;
                                newTagStr = newTagStr.replace(/{VIEW_LINK_RGST}/g, "javascript:openDetail('{VdkVgwKey}', {ARTICLE_IDX}, '', 'biblio', '30', 'View07')") ;
                                newTagStr = newTagStr.replace(/{VIEW_LINK_JUDGEMENT}/g, "javascript:openDetail('{VdkVgwKey}', {ARTICLE_IDX}, '', 'biblio', '{NUMPERPAGE}', 'View08')") ;
				newTagStr = newTagStr.replace(/{VIEW_IMAGE_LINK}/g, "javascript:OpenFrontDrawPop('{VdkVgwKey}')") ;
				newTagStr = newTagStr.replace(/{K2E_LINK}/g, "javascript:goFileCheckTrans('{VdkVgwKey}', 'B1', 'listPage','', 'B1|B1|B1|B1|B1|B1|B1|B1|B1|B1|B1|B1|B1|B1|B1|B1|B1|B1|B1|B1|B1|B1|B1|B1|B1|B1|B1|B1|B1|B1')") ;
                                
                                newTagStr = newTagStr.replace(/{PAGE}/g, "1") ;
				newTagStr = newTagStr.replace(/{ARTICLE_IDX}/g, articleIdx) ;

				newTagStr = newTagStr.replace(/{VdkVgwKey}/g, jQuery(this).find("VdkVgwKey").text()) ;
				newTagStr = newTagStr.replace(/{TTL}/g, TTL) ;
				newTagStr = newTagStr.replace(/{TLT}/g, TLT) ;
				newTagStr = newTagStr.replace(/{TLV}/g, jQuery(this).find("TLV").text()) ;
				newTagStr = newTagStr.replace(/{LST}/g, jQuery(this).find("LST_TXT").text()) ;
				newTagStr = newTagStr.replace(/{IMG_SRC}/g, jQuery(this).find("IMG").find("src").text()) ;
				newTagStr = newTagStr.replace(/{IMG_ALT}/g, jQuery(this).find("IMG").find("alt").text()) ;
				newTagStr = newTagStr.replace(/{IPC}/g, jQuery(this).find("IPV").text()) ;
				newTagStr = newTagStr.replace(/{APV}/g, jQuery(this).find("APV").text()) ;
				newTagStr = newTagStr.replace(/{ADV}/g, dateFormat(jQuery(this).find("ADV").text(), "yyyy.mm.dd")) ;
				newTagStr = newTagStr.replace(/{GNV}/g, jQuery(this).find("GNV").text()) ;
				newTagStr = newTagStr.replace(/{GDV}/g, dateFormat(jQuery(this).find("GDV").text(), "yyyy.mm.dd")) ;
				newTagStr = newTagStr.replace(/{ONV}/g, jQuery(this).find("ONV").text()) ;
				newTagStr = newTagStr.replace(/{ODV}/g, dateFormat(jQuery(this).find("ODV").text(), "yyyy.mm.dd")) ;
				newTagStr = newTagStr.replace(/{AGV}/g, jQuery(this).find("AGV").text()) ;
				newTagStr = newTagStr.replace(/{INV}/g, jQuery(this).find("INV").text()) ;
                                newTagStr = newTagStr.replace(/{NUMPERPAGE}/g, jQuery(xml).find("search").find("page").find("numPerPage").text()) ;

				newTagStr = newTagStr.replace(/{ABV}/g, ABV) ;
                                
                                //By J.H.S 20140704상세정보리스트에 넘기는 index 순서값 추가.
                                articleIdx++; 

				var newTag = jQuery(newTagStr) ;
				$("#patentResultList").append(newTagStr) ;
			}
			catch (e) {
				alert(e) ;
			}
		}
	) ;

}
var SimilarPatentWindow = null;
//유사특허 팝업 열기 by.2017.06
function openKDC(applno)
{
    var userWidth = window.outerWidth;
    var widthSize = '1085'; 

    /* 다중창 서비스 제공으로 수정 202309 KJW
    if (SimilarPatentWindow == null || SimilarPatentWindow.closed)
    {
    	SimilarPatentWindow = window.open("","SimilarPatentWin", 'scrollbars=yes,resizable=yes,width='+ widthSize + ',height=875');
    	SimilarPatentWindow.focus();
    }
    else
    {
        SimilarPatentWindow = window.open("", "SimilarPatentWin", 'scrollbars=yes,resizable=yes,width='+ widthSize + ',height=875');
        SimilarPatentWindow.focus();
    } */
    
    SimilarPatentWindow = window.open("", "SimilarPatentWin-"+applno, 'scrollbars=yes,resizable=yes,width='+ widthSize + ',height=875');
	SimilarPatentWindow.focus();

    var biblioF = document.biblioF;  
    
    //유사특허검색결과
    biblioF.checkPot.value = "S";
    biblioF.queryText.value = applno;   
    biblioF.method = "post";
    biblioF.target = 'SimilarPatentWin-'+applno;
    biblioF.action = "http://kdc.kipris.or.kr/kdc/searchLogina.do?next=SPATSearch";
    biblioF.submit();
    biblioF.target = "";
    
//    //유사특허 통계테이블 저장
//    biblioF.applno.value = applno;
//    biblioF.action = "http://kpat.kipris.or.kr/kpat/biblioa.do?method=spatStat";
//    biblioF.target = 'SimilarPatentWin';
//    biblioF.submit();      
}
/**
 * 초록(div영역)을 보이거나 숨기고, 더보기 버튼과 숨기기 버튼을 토글시킨다. (초록 = 요약)
 * By J.H.S 20141215
 */
function openABVArea(ikey, stat)
{
        var odiv = jQuery("#div_search_detail_" +  ikey);
        var obtn = jQuery("#btnOpenABVArea" +  ikey);
        var cbtn = jQuery("#btnCloseABVArea" +  ikey);
        if(stat == "open")
        {
            odiv.show();
            obtn.hide();
            cbtn.show();
        }
        else if(stat == "close")
        {
            odiv.hide();
            obtn.show();
            cbtn.hide();
        }
}

function setPatentResultCountBoard(V) {
	if (V == void 0 || V == null) {
		jQuery("#patentResultCountBoard").empty() ;
	} else {
		jQuery("#patentResultCountBoard").html(V) ;
	}
}

function setPatentResultViewMode() {
	setPatentResultList(patentResultXmlData) ;
}

function changePatentResultViewMode() {
	patentLoadingDisplay = true ;
	showPatentLoading() ;
	window.setTimeout(setPatentResultViewMode, 500) ;
}

function setPatentResultList(xml) {

	patentLoadingDisplay = false ;
	hidePatentLoading() ;

	jQuery("#patentResultList").empty() ;

	jQuery("#patentResultMore").hide() ;

	var searchResultCount = parseInt(jQuery(xml).find("search").find("searchFound").text()) ;

	if (searchResultCount > 0) {

		addPatentResult(xml) ;

		if (parseInt(jQuery(xml).find("search").find("searchFound").text()) > 0) {

			jQuery("#patentQueryText").val(jQuery(xml).find("search").find("searchKeyword").text()) ;
			jQuery("#patentExpression").val(jQuery(xml).find("search").find("searchExpression").text()) ;
			jQuery("#highlightKeyword").val(jQuery(xml).find("search").find("highlightKeyword").text()) ;

			jQuery("#patentSearchInTrans").val(jQuery(xml).find("search").find("searchExtend").text()) ;

			jQuery("#patentResultMore").show() ;
		}

	} else {
		printPatentSearchException(jQuery(xml).find("message").text()) ;
	}

}

function setPatentResult(xml) {

	if (jQuery(xml).find("flag").text() == "SUCCESS") {

		setPatentResultCountBoard("<em class=\"txt_bold\">" + numberFormat(jQuery(xml).find("search").find("searchFound").text()) + "</em>건 검색") ;

		var searchResultCount = parseInt(jQuery(xml).find("search").find("searchFound").text()) ;

		setPatentSearchResultCount(searchResultCount) ;

		setPatentResultList(xml) ;

	} else {

		patentLoadingDisplay = false ;
		hidePatentLoading() ;

		jQuery("#patentResultList").empty() ;
		jQuery("#patentResultMore").hide() ;

		setPatentSearchResultCount(-1) ;
		printPatentSearchException(jQuery(xml).find("message").text()) ;

	}

}

function printPatentSearchException(V) {

	var newTagStr = "<li>" ;
	newTagStr += "<div class=\"search_section_title\">" ;
	newTagStr += "<h3>" + V + "</h3>" ;
	newTagStr += "</div>" ;
	newTagStr += "</li>" ;

	setPatentResultCountBoard(null) ;

	jQuery("#patentResultList").empty() ;
	jQuery("#patentResultMore").hide() ;

	$("#patentResultList").append(newTagStr) ;

}

var patentFadeTimerId = null ;
var patentFadeValue = 0 ;
var patentLoadingDisplay = true ;
function showPatentLoading() {
	if (patentLoadingDisplay) {

		if (isPageError) {
			if (patentFadeTimerId) {
				window.clearInterval(patentFadeTimerId) ;
				patentFadeTimerId = null ;
				patentFadeValue = 0 ;
			}
			jQuery("#patentResultLoadingBoard").width(jQuery("#patentResultList").width()).height(jQuery("#patentResultList").height()) ;
			jQuery("#patentResultLoadingBoard").css(
							{
								"margin-top" : jQuery("#patentTitle").outerHeight(true)
							}
					) ;

			jQuery("#patentResultLoading").css(
							{
								"margin-top": ((jQuery("#patentResultList").height() / 2) - (jQuery("#patentResultLoading").height() / 2)) + jQuery("#patentTitle").outerHeight(true)
								, "margin-left": parseInt((jQuery("#patentResultList").width() / 2) - (jQuery("#patentResultLoading").width() / 2))
							}
					) ;
			jQuery("#patentResultLoading").show() ;
		} else {

			if (patentFadeTimerId == void 0) {
				patentFadeTimerId = window.setInterval(showPatentLoading, 10) ;
				jQuery("#patentResultLoadingBoard").width(jQuery("#patentResultList").width()).height(jQuery("#patentResultList").height()) ;
				jQuery("#patentResultLoadingBoard").css(
								{
									"margin-top" : jQuery("#patentTitle").outerHeight(true)
								}
						) ;

				jQuery("#patentResultLoading").css(
								{
									"margin-top": ((jQuery("#patentResultList").height() / 2) - (jQuery("#patentResultLoading").height() / 2)) + jQuery("#patentTitle").outerHeight(true)
									, "margin-left": parseInt((jQuery("#patentResultList").width() / 2) - (jQuery("#patentResultLoading").width() / 2))
								}
						) ;

			}
			jQuery("#patentResultLoadingBoard").fadeTo(0, patentFadeValue * 0.08) ;
			if (patentFadeValue >= 10) {
				window.clearInterval(patentFadeTimerId) ;
				patentFadeTimerId = null ;
				jQuery("#patentResultLoading").show() ;
				patentFadeValue = 0 ;
			} else {
				patentFadeValue++ ;
			}
		}
	} else {
		if (patentFadeTimerId) {
			window.clearInterval(patentFadeTimerId) ;
			patentFadeTimerId = null ;
			patentFadeValue = 0 ;
		}
		hidePatentLoading() ;
	}
}

function hidePatentLoading() {
	jQuery("#patentResultLoading").fadeOut(1000) ;
	jQuery("#patentResultLoadingBoard").fadeOut(1000) ;
	jQuery("#patentResultLoadingBoard").width(0).height(0) ;
	jQuery("#patentResultLoading").hide() ;
	jQuery("#patentResultLoadingBoard").hide() ;
}

function getPatentSearchResult(keyword, expression) {

	patentResultXmlData = null ;

	jQuery("#resultPatent").show() ;
	patentLoadingDisplay = true ;
	showPatentLoading() ;

	setPatentResultCountBoard("검색 중입니다.") ;

	setPatentSearchResultCount(-1) ;

	jQuery.ajax({
		type : "POST" ,
		dataType : "xml" ,
		url : "/kportal/resulta.do" ,
		data : {
				next : "patentList"
				, FROM : "SEARCH"
				, searchInTransKorToEng : ((isSearchExtends) ? "Y" : "N")
				, searchInTransEngToKor : ((isSearchExtends) ? "Y" : "N")
				, row : "3"
				, queryText : keyword
				, expression : expression
				, strstat : jQuery("#strstat").val()
		} ,
		success : function(xml, textStatus) {
			patentResultXmlData = xml ;
			setPatentResult(xml) ;
		} ,
		error : function(xhr, textStatus) {
			patentLoadingDisplay = false ;
			hidePatentLoading() ;
			printPatentSearchException("검색 도중 오류가 발생하였습니다.[" + xhr.status + "]") ;
		}
	}) ;
}


</script>



<script type="text/javascript">
 
var BigImageDG = null ;
function GoBigImageDG(masterKey, IMP)
{
	/* 다중창 서비스 제공으로 수정 202309 KJW
	if (BigImageDG != null && !BigImageDG.closed)
	{
		BigImageDG.close() ;
	}
	BigImageDG = window.open("https://www.kipris.or.kr/kdtj/wpages/result/SRIM1000.jsp?method=bigImageDG&masterKey=" + masterKey + "&no=" + IMP, "BigImage", "status=yes, resizable=yes, width=650, height=700 , scrollbars=yes, top=10, left=20"); */
	BigImageDG = window.open("https://www.kipris.or.kr/kdtj/wpages/result/SRIM1000.jsp?method=bigImageDG&masterKey=" + masterKey + "&no=" + IMP, "BigImage-" + masterKey, "status=yes, resizable=yes, width=650, height=700 , scrollbars=yes, top=10, left=20");
	BigImageDG.focus() ;
}

</script>
<form name="designMoreFrm" id="designMoreFrm" method="post">
				<section id="resultDesign" class="search_section">
					<div id="designResultLoadingBoard"></div>
					<div id="designResultLoading"><img src="/kportal/images/common/loading_design.gif" alt="디자인 검색결과를 불러오고 있습니다." /></div>
					<h2 id="designTitle" class="total_title">[디자인] <button type="submit" id="moreDesignResult2" ><span id="designResultCountBoard"><em class="txt_bold"></em>건 검색</span></button></h2>
					<div id="designResultList">
						<div class="search_blank"></div>
					</div>
<input type="hidden" name="next" value="design" />
<input type="hidden" id="designQueryText" name="queryText" value="" />
<input type="hidden" id="designExpression" name="expression" value="" />
<input type="hidden" id="designSearchInTrans" name="searchInTrans" value="" />
<input type="hidden" name="config" value="G1111111111111111111111S110001000000000000" />
<input type="hidden" name="SEL_PAT" value="DG" />
<input type="hidden" name="sortField1" value="Score" />
<input type="hidden" name="sortState1" value="Desc" />
<input type="hidden" name="currentPage" value="1" />
<input type="hidden" name="numPerPage" value="30" />
					<p id="designResultMore" class="total_more">
                                                <span class="more_plus"><button type="submit" id="goDesignResult" >디자인 <span style="color:#00a13a">더보기</span></button></span>
						<span class="more"><button type="submit" id="moreDesignResult" >통합검색 <span style="color:#00a13a"> 더보기</span></button></span>
					</p>
				</section>
</form>
				
<script type="text/javascript">

function dlstdescopen(){
    newPopupWindow('http://www.kipris.or.kr/khome/help/help02/help02_2.jsp#chapter3','HelpWin',820, 800, 'C', 'M', 'scrollbars=yes');
}

jQuery("#moreDesignResult").click(
	function(evt) {
		jQuery("#designMoreFrm").prop("action", "/kportal/search/search_design.do") ;
	}
) ;
jQuery("#moreDesignResult2").click(
	function(evt) {
		jQuery("#designMoreFrm").prop("action", "/kportal/search/search_design.do") ;
	}
) ;
jQuery("#goDesignResult").click(
	function(evt) {
		var queryText = jQuery("#designQueryText").val() ;
		var expression = jQuery("#designExpression").val() ;
		jQuery("#designQueryText").val(queryText) ;
		jQuery("#designExpression").val(expression) ;
		jQuery("#designMoreFrm").prop("action", "http://kdtj.kipris.or.kr/kdtj/searchLogina.do?method=loginDG&checkPot=Y") ;
                //jQuery("#designMoreFrm").prop("action", "https://www.kipris.or.kr/kdtj/grrt1000a.do?method=searchDG&next=ResultListDG") ;
	}
) ;

var designResultXmlData = null ;

function addDesignResult(xml) {

	var articleIdx = 0 ;
	jQuery(xml).find("search").find("articles").find("article").each(
		function(idx) {

			var newTagStr = "" ;
                        var ds_seq = jQuery(this).find("DS_SEQ").text();
                        //20141203 pdy 국제등록번호(일자) 추가
                        var hn     = jQuery(this).find("HN").text();
                        var hd     = jQuery(this).find("HD").text();
			if (resultViewMode == "TEXT") {

				newTagStr += '<article>' ;
				newTagStr += '	<div class="search_section_title">' ;
				//newTagStr += '		<span class="float_left"><input type="checkbox" id="search_extend" /></span>' ;
				//By J.H.S 20160615 국제디자인의 경우 영문 물품명칭을 보이도록 함
                                if(jQuery(this).find("ITE").text() == "" || jQuery(this).find("ITE").text() == " ") {
                                    newTagStr += '		<h1 class="stitle"><a href="javascript:dlstdescopen();" title="행정상태 도움말 새창으로 열림"><span class="{LST_CSS}">{LST}</span></a> <a href="{VIEW_LINK}" title="새창으로 열림">{IT}</a></h1>' ;
                                }
                                else{
                                    newTagStr += '		<h1 class="stitle"><a href="javascript:dlstdescopen();" title="행정상태 도움말 새창으로 열림"><span class="{LST_CSS}">{LST}</span></a> <a href="{VIEW_LINK}" title="새창으로 열림">{IT}\({ITE}\)</a></h1>' ;
                                }
                                
                                newTagStr += '		<div class="btn_doc">' ;
                                
                                if (jQuery(this).find("JMFLAG").text() == "Y") {
                                        newTagStr += ' <a href="{VIEW_LINK_JUGEMENT}" title="심판사항 새창으로 열림"><img src="/kportal/images/button/btn_judgment.gif" alt="심판사항" /></a>' ;
                                }
                                
                                if (jQuery(this).find("PUBFG").text() == "R") {
                                        newTagStr += ' <a href="{FULLTEXT_VIEW}" title="등록공보 새창으로 열림"><img src="/kportal/images/button/btn_kor.gif" alt="등록공보" /></a>' ;
                                }
                                
                                if (jQuery(this).find("PUBFG").text() == "B") {
                                        newTagStr += ' <a href="{VIEW_LINK_BOOK}" title="책자공보 새창으로 열림"><img src="/kportal/images/button/btn_kor.gif" alt="책자공보" /></a>' ;
                                }
                                
                                if (jQuery(this).find("PUBFG").text() == "P") {
                                        newTagStr += ' <a href="{VIEW_LINK_PUBLIC}" title="공개공보 새창으로 열림"><img src="/kportal/images/button/btn_kor.gif" alt="공개공보" /></a>' ;
                                }
                                
                                newTagStr += '	        </div>' ;
				newTagStr += '	</div>' ;
				newTagStr += '	<div class="search_basic_info">' ;
				newTagStr += '		<ul class="noimg_list">' ;
				if(jQuery(this).find("DC").text()=="비밀디자인 비공개 항목"){
					newTagStr += '			<li class="left_width"><span>한국분류 :</span> <span>{DC}</span></li>' ;
	                newTagStr += '			<li class="right_width"><span>국제분류 :</span> <span>{LC}</span></li>' ;								
				}else{
					newTagStr += '			<li class="left_width"><span>한국분류 :</span> <span class="point01">{DC}</span></li>' ;
	                newTagStr += '			<li class="right_width"><span>국제분류 :</span> <span class="point01">{LC}</span></li>' ;					
				}

                                //20141203 pdy 국제등록번호(일자) 추가
				if(ds_seq.length>3){
                                    if(hn.length>1){
                                        newTagStr += '			<li class="left_width"><span>국제등록번호 :</span> <a href="{VIEW_LINK}" title="새창으로 열림"><span class="point01">{HN}\({DS_SEQ}\)</span></a></li>' ;
                                    }else{
                                        newTagStr += '			<li class="left_width"><span>출원번호 :</span> <a href="{VIEW_LINK}" title="새창으로 열림"><span class="point01">{ANN}\({DS_SEQ}\)</span></a></li>' ;
                                    }
                                    
                                }else{
                                    if(hn.length>1){
                                        newTagStr += '			<li class="left_width"><span>국제등록번호 :</span> <a href="{VIEW_LINK}" title="새창으로 열림"><span class="point01">{HN}</span></a></li>' ;
                                    }else{
                                        newTagStr += '			<li class="left_width"><span>출원번호 :</span> <a href="{VIEW_LINK}" title="새창으로 열림"><span class="point01">{ANN}</span></a></li>' ;
                                    }    
                                }
                                if(hd.length>1){
                                    newTagStr += '			<li class="right_width"><span>국제등록일자 :</span> {HD}</li>' ;
                                }else{
                                    newTagStr += '			<li class="right_width"><span>출원일자 :</span> {AD}</li>' ;
                                }
                                if(hd.length>1){
                                    newTagStr += '			<li class="left_width"><span>등록번호 :</span></li>' ;
                                }else{
                                    if ((jQuery(this).find("RNN").text() == "") || (jQuery(this).find("RNN").text() == " ")) {
                                        newTagStr += '			<li class="left_width"><span>등록번호 :</span></li>' ;
                                    }
                                    else{
                                        newTagStr += '			<li class="left_width"><span>등록번호 :</span> <a href="{VIEW_LINK_RGST}" title="새창으로 열림"><span class="point01">{RNN}</span></a></li>' ;
                                    }
                                }
                                newTagStr += '			<li class="right_width"><span>등록일자 :</span> {RD}</li>' ;
				newTagStr += '			<li class="left_width"><span>공개번호 :</span> {ONN}</li>' ;
				newTagStr += '			<li class="right_width"><span>공개일자 :</span> {OD}</li>' ;
				newTagStr += '			<li class="left_width letter1"><span>출원인 :</span> <font title="{APNM}">{APNM}</font></li>' ;
                                newTagStr += '			<li class="right_width"><span>창작자 :</span> <font title="{IVN}">{IVN}</font></li>' ;
                                //newTagStr += '			<li class="left_width"><span>대리인 :</span> <font title="{AGNM}">{AGNM}</font></li>' ;
                                newTagStr += '		</ul>' ;
                                newTagStr += '	        <div class="search_detail_content">' ;
                                newTagStr += '	                <ul class="search_setList"></ul>' ;
                                newTagStr += '	                <div class="search_txt">' ;
                                newTagStr += '	                        {INVNTR_SUMMARY}' ;
                                newTagStr += '	                </div class="search_txt">' ;
                                newTagStr += '	                <div class="btn_area"></div>' ;
                                newTagStr += '	        </div>' ;
				newTagStr += '	</div>' ;
				newTagStr += '</article>' ;

			} else {

				newTagStr += '<article>' ;
				newTagStr += '	<div class="search_section_title">' ;
				//newTagStr += '		<span class="float_left"><input type="checkbox" id="search_extend" /></span>' ;
				//By J.H.S 20160615 국제디자인의 경우 영문 물품명칭을 보이도록 함
                                if(jQuery(this).find("ITE").text() == "" || jQuery(this).find("ITE").text() == " ") {
                                    newTagStr += '		<h1 class="stitle"><a href="javascript:dlstdescopen();" title="행정상태 도움말 새창으로 열림"><span class="{LST_CSS}">{LST}</span></a> <a href="{VIEW_LINK}" title="새창으로 열림">{IT}</a></h1>' ;
                                }
                                else{
                                    newTagStr += '		<h1 class="stitle"><a href="javascript:dlstdescopen();" title="행정상태 도움말 새창으로 열림"><span class="{LST_CSS}">{LST}</span></a> <a href="{VIEW_LINK}" title="새창으로 열림">{IT}\({ITE}\)</a></h1>' ;
                                }
                                
				newTagStr += '		<div class="btn_doc">' ;
                                
                                if (jQuery(this).find("JMFLAG").text() == "Y") {
                                        newTagStr += ' <a href="{VIEW_LINK_JUGEMENT}" title="심판사항 새창으로 열림"><img src="/kportal/images/button/btn_judgment.gif" alt="심판사항" /></a>' ;
                                }
                                
                                if (jQuery(this).find("PUBFG").text() == "R") {
                                        newTagStr += ' <a href="{FULLTEXT_VIEW}" title="등록공보 새창으로 열림"><img src="/kportal/images/button/btn_kor.gif" alt="등록공보" /></a>' ;
                                }
                                
                                if (jQuery(this).find("PUBFG").text() == "B") {
                                        newTagStr += ' <a href="{VIEW_LINK_BOOK}" title="책자공보 새창으로 열림"><img src="/kportal/images/button/btn_kor.gif" alt="책자공보" /></a>' ;
                                }
                                
                                if (jQuery(this).find("PUBFG").text() == "P") {
                                        newTagStr += ' <a href="{VIEW_LINK_PUBLIC}" title="공개공보 새창으로 열림"><img src="/kportal/images/button/btn_kor.gif" alt="공개공보" /></a>' ;
                                }
                                
                                newTagStr += '	        </div>' ;
				newTagStr += '	</div>' ;
				newTagStr += '	<div class="search_basic_info">' ;
				
                                if (jQuery(this).find("IMG").find("alt").text() == "이미지 없음") {
                                        newTagStr += '		<div class="thumb"><img src="{IMG_SRC}" width="100" height="100" alt="{IMG_ALT}" /></div>' ;
                                }else if(jQuery(this).find("IMG").find("alt").text() == "비밀디자인"){
                            	    newTagStr += '		<div class="thumb"><img src="{IMG_SRC}" width="100" height="100" alt="{IMG_ALT}" /></div>' ;
                            	}else{
                                        newTagStr += '		<div class="thumb"><a href="{VIEW_IMAGE_LINK}" title="새창으로 열림"><img src="{IMG_SRC}" width="100" height="100" alt="{IMG_ALT}" /></a></div>' ;
                                }
				
                                newTagStr += '		<ul class="search_info_list">' ;
                                if(jQuery(this).find("DC").text()=="비밀디자인 비공개 항목"){
                					newTagStr += '			<li class="left_width"><span>한국분류 :</span> <span>{DC}</span></li>' ;
                	                newTagStr += '			<li class="right_width"><span>국제분류 :</span> <span>{LC}</span></li>' ;								
                				}else{
                					newTagStr += '			<li class="left_width"><span>한국분류 :</span> <span class="point01">{DC}</span></li>' ;
                	                newTagStr += '			<li class="right_width"><span>국제분류 :</span> <span class="point01">{LC}</span></li>' ;					
                				}
				//20141203 pdy 국제등록번호(일자) 추가
                                if(ds_seq.length>3){
                                    if(hn.length>1){
                                        newTagStr += '			<li class="left_width"><span>국제등록번호 :</span> <a href="{VIEW_LINK}" title="새창으로 열림"><span class="point01">{HN}\({DS_SEQ}\)</span></a></li>' ;
                                    }else{
                                        newTagStr += '			<li class="left_width"><span>출원번호 :</span> <a href="{VIEW_LINK}" title="새창으로 열림"><span class="point01">{ANN}\({DS_SEQ}\)</span></a></li>' ;
                                    }     
                                }else{
                                    if(hn.length>1){
                                        newTagStr += '			<li class="left_width"><span>국제등록번호 :</span> <a href="{VIEW_LINK}" title="새창으로 열림"><span class="point01">{HN}</span></a></li>' ;
                                    }else{
                                        newTagStr += '			<li class="left_width"><span>출원번호 :</span> <a href="{VIEW_LINK}" title="새창으로 열림"><span class="point01">{ANN}</span></a></li>' ;
                                    }    
                                }
                                if(hd.length>1){
                                    newTagStr += '			<li class="right_width"><span>국제등록일자 :</span> {HD}</li>' ;
                                }else{
                                    newTagStr += '			<li class="right_width"><span>출원일자 :</span> {AD}</li>' ;
                                }	
				if(hd.length>1){
                                    newTagStr += '			<li class="left_width"><span>등록번호 :</span></li>' ;
                                }else{
                                    if ((jQuery(this).find("RNN").text() == "") || (jQuery(this).find("RNN").text() == " ")) {
                                        newTagStr += '			<li class="left_width"><span>등록번호 :</span></li>' ;
                                    }
                                    else{
                                        newTagStr += '			<li class="left_width"><span>등록번호 :</span> <a href="{VIEW_LINK_RGST}" title="새창으로 열림"><span class="point01">{RNN}</span></a></li>' ;
                                    }
                                }
                                newTagStr += '			<li class="right_width"><span>등록일자 :</span> {RD}</li>' ;
				newTagStr += '			<li class="left_width"><span>공개번호 :</span> {ONN}</li>' ;
				newTagStr += '			<li class="right_width"><span>공개일자 :</span> {OD}</li>' ;
				newTagStr += '			<li class="left_width letter1"><span>출원인 :</span> <font title="{APNM}">{APNM}</font></li>' ;
                                newTagStr += '			<li class="right_width"><span>창작자 :</span> <font title="{IVN}">{IVN}</font></li>' ;
                                //newTagStr += '			<li class="left_width"><span>대리인 :</span> <font title="{AGNM}">{AGNM}</font></li>' ;
                                newTagStr += '		</ul>' ;
                                newTagStr += '          <div id="btnOpenInvntrSummaryArea{VdkVgwKey_INVNTR_SUMMARY}" class="btn_close"><span class="more"><a href="{INVNTR_SUMMARY_OPEN}">열기</a></span></div>' ;
                                newTagStr += '		<div id="div_search_detail_{VdkVgwKey_INVNTR_SUMMARY}" class="search_detail_content" style="display:none">' ;
                                newTagStr += '	                <ul class="search_setList">' ;
                                newTagStr += '	                        <li class="left_width"><span>대리인 :</span> {AGNM}</li>' ;
                                newTagStr += '	                </ul>' ;
                                newTagStr += '	                <div class="search_txt">' ;
                                newTagStr += '	                        <span>창작의 요점 :</span> {INVNTR_SUMMARY}' ;
				newTagStr += '	</div>' ;
                                newTagStr += '                  <div id="btnCloseInvntrSummaryArea{VdkVgwKey_INVNTR_SUMMARY}" class="btn_close"><span class="close"><a href="{INVNTR_SUMMARY_CLOSE}">닫기</a></span></div>' ;
                                newTagStr += '	        </div>' ;
				newTagStr += '	</div>' ;
				newTagStr += '</article>' ;

			}

			var LAS = jQuery(this).find("LAS").text() ;
                        
                        newTagStr = newTagStr.replace(/{INVNTR_SUMMARY_OPEN}/g, "javascript:openInvntrSummaryArea('{VdkVgwKey_INVNTR_SUMMARY}', 'open')") ;
                        newTagStr = newTagStr.replace(/{INVNTR_SUMMARY_CLOSE}/g, "javascript:openInvntrSummaryArea('{VdkVgwKey_INVNTR_SUMMARY}', 'close')") ;
                        newTagStr = newTagStr.replace(/{VdkVgwKey_INVNTR_SUMMARY}/g, jQuery(this).find("VdkVgwKey").text().replace(",", "")) ;
                        //20141208 pdy 국제등록번호 추가
                        //GoBibliography 함수 인자 값추가에 따른 수정 20150209 jkc
                        if(hn.length>1){
                            newTagStr = newTagStr.replace(/{VIEW_LINK}/g, "javascript:GoBibliography('DG', '{VdkVgwKey}', '{ARTICLE_IDX}', 'A', '', 'View01', '{HN}')") ;
                            newTagStr = newTagStr.replace(/{VIEW_LINK_PUBLIC}/g, "javascript:GoBibliography('DG', '{VdkVgwKey}', '{ARTICLE_IDX}', 'A', '', 'View02', '{HN}')") ;
                            newTagStr = newTagStr.replace(/{FULLTEXT_VIEW}/g, "javascript:GoBibliography('DG', '{VdkVgwKey}', '{ARTICLE_IDX}', 'F', '', 'View03', '{HN}')") ;
                            newTagStr = newTagStr.replace(/{VIEW_LINK_BOOK}/g, "javascript:GoBibliography('DG', '{VdkVgwKey}', '{ARTICLE_IDX}', 'F', '', 'View04', '{HN}')") ;
                            newTagStr = newTagStr.replace(/{VIEW_LINK_RGST}/g, "javascript:GoBibliography('DG', '{VdkVgwKey}', '{ARTICLE_IDX}', 'A', '', 'View06', '{HN}')") ;
                            newTagStr = newTagStr.replace(/{VIEW_LINK_JUGEMENT}/g, "javascript:GoBibliography('DG', '{VdkVgwKey}', '{ARTICLE_IDX}', 'F', '', 'View07', '{HN}')") ;
                        }else{
                            newTagStr = newTagStr.replace(/{VIEW_LINK}/g, "javascript:GoBibliography('DG', '{VdkVgwKey}', '{ARTICLE_IDX}', 'A', '', 'View01','{HN}')") ;
                            newTagStr = newTagStr.replace(/{VIEW_LINK_PUBLIC}/g, "javascript:GoBibliography('DG', '{VdkVgwKey}', '{ARTICLE_IDX}', 'A', '', 'View02','{HN}')") ;
                            newTagStr = newTagStr.replace(/{FULLTEXT_VIEW}/g, "javascript:GoBibliography('DG', '{VdkVgwKey}', '{ARTICLE_IDX}', 'F', '', 'View03','{HN}')") ;
                            newTagStr = newTagStr.replace(/{VIEW_LINK_BOOK}/g, "javascript:GoBibliography('DG', '{VdkVgwKey}', '{ARTICLE_IDX}', 'F', '', 'View04','{HN}')") ;
                            newTagStr = newTagStr.replace(/{VIEW_LINK_RGST}/g, "javascript:GoBibliography('DG', '{VdkVgwKey}', '{ARTICLE_IDX}', 'A', '', 'View06','{HN}')") ;
                            newTagStr = newTagStr.replace(/{VIEW_LINK_JUGEMENT}/g, "javascript:GoBibliography('DG', '{VdkVgwKey}', '{ARTICLE_IDX}', 'F', '', 'View07','{HN}')") ;
                        }
			
			newTagStr = newTagStr.replace(/{VIEW_IMAGE_LINK}/g, "javascript:GoBigImageDG('{VdkVgwKey}','{IMP_SEQ}')") ;
			newTagStr = newTagStr.replace(/{TYPE}/g, "DG") ;
			newTagStr = newTagStr.replace(/{PAGE}/g, jQuery(xml).find("search").find("page").find("searchPage").text()) ;
			newTagStr = newTagStr.replace(/{ARTICLE_IDX}/g, articleIdx) ;
			newTagStr = newTagStr.replace(/{IT}/g, jQuery(this).find("IT").text()) ;
                        newTagStr = newTagStr.replace(/{ITE}/g, jQuery(this).find("ITE").text()) ;
			newTagStr = newTagStr.replace(/{LST}/g, jQuery(this).find("LST").text()) ;
			if (jQuery(this).find("LST").text() == "") {
				LAS = "" ;
			}
			switch (LAS) {
				case "A" :
					newTagStr = newTagStr.replace(/{LST_CSS}/g, "box_small_a") ; break ;
				case "B" :
					newTagStr = newTagStr.replace(/{LST_CSS}/g, "box_small_b") ; break ;
				case "J" :
					newTagStr = newTagStr.replace(/{LST_CSS}/g, "box_small_j") ; break ;
				case "R" :
					newTagStr = newTagStr.replace(/{LST_CSS}/g, "box_small_r") ; break ;
				case "F" :
					newTagStr = newTagStr.replace(/{LST_CSS}/g, "box_small_f") ; break ;
				case "I" :
					newTagStr = newTagStr.replace(/{LST_CSS}/g, "box_small_i") ; break ;
				case "C" :
					newTagStr = newTagStr.replace(/{LST_CSS}/g, "box_small_c") ; break ;
				case "G" :
					newTagStr = newTagStr.replace(/{LST_CSS}/g, "box_small_g") ; break ;
				default :
					newTagStr = newTagStr.replace(/{LST_CSS}/g, "") ; break ;
                        }
                        newTagStr = newTagStr.replace(/{VdkVgwKey}/g, jQuery(this).find("VdkVgwKey").text()) ;             //출원번호
			newTagStr = newTagStr.replace(/{IMG_SRC}/g, jQuery(this).find("IMG").find("src").text()) ;         //이미지 경로
			newTagStr = newTagStr.replace(/{IMG_ALT}/g, jQuery(this).find("IMG").find("alt").text()) ;         //이미지 alt속성
			newTagStr = newTagStr.replace(/{DC}/g, jQuery(this).find("DC").text()) ;                           //의장분류
                        newTagStr = newTagStr.replace(/{FC}/g, jQuery(this).find("FC").text()) ;                           //형태분류코드
                        newTagStr = newTagStr.replace(/{LC}/g, jQuery(this).find("LC").text()) ;                           //로카르노코드 
			newTagStr = newTagStr.replace(/{APNM}/g, jQuery(this).find("APNM").text()) ;                       //출원인
			newTagStr = newTagStr.replace(/{ANN}/g, jQuery(this).find("ANN").text()) ;                         //출원번호
			newTagStr = newTagStr.replace(/{AD}/g, dateFormat(jQuery(this).find("AD").text(), "yyyy.mm.dd")) ; //출원일자
			newTagStr = newTagStr.replace(/{RNN}/g, jQuery(this).find("RNN").text()) ;                         //등록번호
			newTagStr = newTagStr.replace(/{RD}/g, dateFormat(jQuery(this).find("RD").text(), "yyyy.mm.dd")) ; //등록일자
			newTagStr = newTagStr.replace(/{ONN}/g, jQuery(this).find("ONN").text()) ;                         //공개번호
			newTagStr = newTagStr.replace(/{OD}/g, dateFormat(jQuery(this).find("OD").text(), "yyyy.mm.dd")) ; //공개일자
			newTagStr = newTagStr.replace(/{IVN}/g, jQuery(this).find("IVN").text()) ;                         //창작자
			newTagStr = newTagStr.replace(/{AGNM}/g, jQuery(this).find("AGNM").text()) ;                       //대리인
                        newTagStr = newTagStr.replace(/{IMP_SEQ}/g, jQuery(this).find("IMP_SEQ").text()) ;                 //견본이미지 seq
                        newTagStr = newTagStr.replace(/{DS_SEQ}/g, ds_seq) ;                                               //디자인 일련번호
                        newTagStr = newTagStr.replace(/{INVNTR_SUMMARY}/g, jQuery(this).find("INVNTR_SUMMARY").text()) ;   //창작의 요점
                        
                        //20141203 pdy 국제등록번호(일자) 추가
                        newTagStr = newTagStr.replace(/{HN}/g, hn) ;       
                        newTagStr = newTagStr.replace(/{HD}/g, dateFormat(hd, "yyyy.mm.dd")) ;       

			var newTag = jQuery(newTagStr) ;
			$("#designResultList").append(newTag) ;

			articleIdx++ ;

		}
	) ;

}

/**
 * 창작의 요점(div영역)을 보이거나 숨기고, 더보기 버튼과 숨기기 버튼을 토글시킨다.
 * By J.H.S 20141215
 */
function openInvntrSummaryArea(ikey, stat)
{
        var odiv = jQuery("#div_search_detail_" +  ikey);
        var obtn = jQuery("#btnOpenInvntrSummaryArea" +  ikey);
        var cbtn = jQuery("#btnCloseInvntrSummaryArea" +  ikey);

        if(stat == "open")
        {
            odiv.show();
            obtn.hide();
            cbtn.show();
        }
        else if(stat == "close")
        {
            odiv.hide();
            obtn.show();
            cbtn.hide();
        }
}

function setDesignResultCountBoard(V) {
	if (V == void 0 || V == null) {
		jQuery("#designResultCountBoard").empty() ;
	} else {
		jQuery("#designResultCountBoard").html(V) ;
	}
}

function setDesignResultViewMode() {
	setDesignResultList(designResultXmlData) ;
}

function changeDesignResultViewMode() {
	designLoadingDisplay = true ;
	showDesignLoading() ;
	window.setTimeout(setDesignResultViewMode, 500) ;
}

function setDesignResultList(xml) {

	designLoadingDisplay = false ;
	hideDesignLoading() ;

	jQuery("#designResultList").empty() ;

	jQuery("#designResultMore").hide() ;

	var searchResultCount = parseInt(jQuery(xml).find("search").find("searchFound").text()) ;

	if (searchResultCount > 0) {

		addDesignResult(xml) ;

		if (parseInt(jQuery(xml).find("search").find("searchFound").text()) > 0) {

			jQuery("#designQueryText").val(jQuery(xml).find("search").find("searchKeyword").text()) ;
			jQuery("#designExpression").val(jQuery(xml).find("search").find("searchExpression").text()) ;

			jQuery("#designSearchInTrans").val(jQuery(xml).find("search").find("searchExtend").text()) ;

			jQuery("#designResultMore").show() ;
		}

	} else {
		printDesignSearchException(jQuery(xml).find("message").text()) ;
	}

}

function setDesignResult(xml) {

	if (jQuery(xml).find("flag").text() == "SUCCESS") {

		setDesignResultCountBoard("<em class=\"txt_bold\">" + numberFormat(jQuery(xml).find("search").find("searchFound").text()) + "</em>건 검색") ;

		var searchResultCount = parseInt(jQuery(xml).find("search").find("searchFound").text()) ;
                    
		setDesignSearchResultCount(searchResultCount) ;
            
		setDesignResultList(xml) ;

	} else {

		designLoadingDisplay = false ;
		hideDesignLoading() ;

		jQuery("#designResultList").empty() ;
		jQuery("#designResultMore").hide() ;

		setDesignSearchResultCount(-1) ;
		printDesignSearchException(jQuery(xml).find("message").text()) ;

	}

}

function printDesignSearchException(V) {

	var newTagStr = "<li>" ;
	newTagStr += "<div class=\"search_section_title\">" ;

	newTagStr += "<h3>" + V + "</h3>" ;
	newTagStr += "</div>" ;
	newTagStr += "</li>" ;

	setDesignResultCountBoard(null) ;

	jQuery("#designResultList").empty() ;
	jQuery("#designResultMore").hide() ;

	$("#designResultList").append(newTagStr) ;

}

var designFadeTimerId = null ;
var designFadeValue = 0 ;
var designLoadingDisplay = true ;
function showDesignLoading() {
	if (designLoadingDisplay) {

		if (isPageError) {
			if (designFadeTimerId) {
				window.clearInterval(designFadeTimerId) ;
				designFadeTimerId = null ;
				designFadeValue = 0 ;
			}
			jQuery("#designResultLoadingBoard").width(jQuery("#designResultList").width()).height(jQuery("#designResultList").height()) ;
			jQuery("#designResultLoadingBoard").css(
							{
								"margin-top" : jQuery("#designTitle").outerHeight(true)
							}
					) ;

			jQuery("#designResultLoading").css(
							{
								"margin-top": ((jQuery("#designResultList").height() / 2) - (jQuery("#designResultLoading").height() / 2)) + jQuery("#designTitle").outerHeight(true)
								, "margin-left": parseInt((jQuery("#designResultList").width() / 2) - (jQuery("#designResultLoading").width() / 2))
							}
					) ;
			jQuery("#designResultLoading").show() ;
		} else {

			if (designFadeTimerId == void 0) {
				designFadeTimerId = window.setInterval(showDesignLoading, 10) ;
				jQuery("#designResultLoadingBoard").width(jQuery("#designResultList").width()).height(jQuery("#designResultList").height()) ;
				jQuery("#designResultLoadingBoard").css(
								{
									"margin-top" : jQuery("#designTitle").outerHeight(true)
								}
						) ;

				jQuery("#designResultLoading").css(
								{
									"margin-top": ((jQuery("#designResultList").height() / 2) - (jQuery("#designResultLoading").height() / 2)) + jQuery("#designTitle").outerHeight(true)
									, "margin-left": parseInt((jQuery("#designResultList").width() / 2) - (jQuery("#designResultLoading").width() / 2))
								}
						) ;

			}
			jQuery("#designResultLoadingBoard").fadeTo(0, designFadeValue * 0.08) ;
			if (designFadeValue >= 10) {
				window.clearInterval(designFadeTimerId) ;
				designFadeTimerId = null ;
				jQuery("#designResultLoading").show() ;
				designFadeValue = 0 ;
			} else {
				designFadeValue++ ;
			}
		}
	} else {
		if (designFadeTimerId) {
			window.clearInterval(designFadeTimerId) ;
			designFadeTimerId = null ;
			designFadeValue = 0 ;
		}
		hideDesignLoading() ;
	}
}

function hideDesignLoading() {
	jQuery("#designResultLoading").fadeOut(1000) ;
	jQuery("#designResultLoadingBoard").fadeOut(1000) ;
	jQuery("#designResultLoadingBoard").width(0).height(0) ;
	jQuery("#designResultLoading").hide() ;
	jQuery("#designResultLoadingBoard").hide() ;
}

function getDesignSearchResult(keyword, expression) {

	designResultXmlData = null ;

	jQuery("#resultDesign").show() ;
	designLoadingDisplay = true ;
	showDesignLoading() ;

	setDesignResultCountBoard("검색 중입니다.") ;

	setDesignSearchResultCount(-1) ;

	jQuery.ajax({
		type : "POST" ,
		dataType : "xml" ,
		url : "/kportal/resulta.do" ,
		data : {
				next : "designList"
				, FROM : "SEARCH"
				, searchInTransKorToEng : ((isSearchExtends) ? "Y" : "N")
				, searchInTransEngToKor : ((isSearchExtends) ? "Y" : "N")
				, row : "3"
				, queryText : keyword
				, expression : expression
		} ,
		success : function(xml, textStatus) {
			designResultXmlData = xml ;
			setDesignResult(xml) ;
		} ,
		error : function(xhr, textStatus) {
			designLoadingDisplay = false ;
			hideDesignLoading() ;
			printDesignSearchException("검색 도중 오류가 발생하였습니다.[" + xhr.status + "]") ;
		}
	}) ;
}


</script>



<script type="text/javascript">

var BigImageTM = null ;
function GoBigImageTM(masterKey, imgNm)
{
	/* 다중창 서비스 제공으로 수정 202309 KJW
	if (BigImageTM != null && !BigImageTM.closed)
	{
		BigImageTM.close() ;
	}
	BigImageTM = window.open("https://www.kipris.or.kr/kdtj/wpages/result/SRIM1000.jsp?method=bigImageTM&applno=" + masterKey + "&no=" + imgNm, "BigImage", "status=yes, resizable=yes, width=650, height=700 , scrollbars=yes, top=10, left=20"); */
	BigImageTM = window.open("https://www.kipris.or.kr/kdtj/wpages/result/SRIM1000.jsp?method=bigImageTM&applno=" + masterKey + "&no=" + imgNm, "BigImage-" + masterKey, "status=yes, resizable=yes, width=650, height=700 , scrollbars=yes, top=10, left=20");
	BigImageTM.focus() ;
}

</script>
<form name="trademarkMoreFrm" id="trademarkMoreFrm" method="post">
				<section id="resultTrademark" class="search_section">
					<div id="trademarkResultLoadingBoard"></div>
					<div id="trademarkResultLoading"><img src="/kportal/images/common/loading_trademark.gif" alt="상표 검색결과를 불러오고 있습니다." /></div>
					<h2 id="trademarkTitle" class="total_title">[상표] <button type="submit" id="moreTrademarkResult2" ><span id="trademarkResultCountBoard"><em class="txt_bold"></em>건 검색</span></button></h2>
					<div id="trademarkResultList">
						<div class="search_blank"></div>

					</div>
<input type="hidden" name="next" value="trademark" />
<input type="hidden" id="trademarkQueryText" name="queryText" value="" />
<input type="hidden" id="trademarkExpression" name="expression" value="" />
<input type="hidden" id="trademarkSearchInTrans" name="searchInTrans" value="" />
<input type="hidden" name="merchandiseString" value="td40,td41,td42,td43,td44,td45,td47,td48,tdmd," />
<input type="hidden" name="config" value="G1111111111111111111111S110001000000000000" />
<input type="hidden" name="measureString" value="A,B,J,R,F,I,C,G," />
<input type="hidden" name="patternString" value="letter,figure,lmixed,fmixed,sounds,fragre," />
					<p id="trademarkResultMore" class="total_more">
						<span class="more"><button type="submit" id="moreTrademarkResult" >통합검색 <span style="color:#00a13a">더보기</span></button></span>
                                                <span class="more_plus"><button type="submit" id="goTrademarkResult" >상표 <span style="color:#00a13a">더보기</span></button></span>
					</p>
                                </section>
</form>
				
<script type="text/javascript">

function tlstdescopen(){
    newPopupWindow('http://www.kipris.or.kr/khome/help/help04/help04_2.jsp#chapter4','HelpWin',820, 800, 'C', 'M', 'scrollbars=yes');
}

jQuery("#moreTrademarkResult").click(
	function(evt) {
		jQuery("#trademarkMoreFrm").prop("action", "/kportal/search/search_trademark.do") ;
	}
) ;
jQuery("#moreTrademarkResult2").click(
	function(evt) {
		jQuery("#trademarkMoreFrm").prop("action", "/kportal/search/search_trademark.do") ;
	}
) ;
jQuery("#goTrademarkResult").click(
	function(evt) {
                jQuery("#trademarkMoreFrm").prop("action", "https://www.kipris.or.kr/kdtj/searchLogina.do?method=loginTM&checkPot=Y") ;
	}
) ;

var trademarkResultXmlData = null ;

function addTrademarkResult(xml) {
	var articleIdx = 0 ;
	jQuery(xml).find("search").find("articles").find("article").each(
		function(idx) {

			var newTagStr = "" ;

			if (resultViewMode == "TEXT") {

				newTagStr += '<article>' ;
				newTagStr += '	<div class="search_section_title">' ;
				//newTagStr += '		<span class="float_left"><input type="checkbox" id="search_extend" /></span>' ;
				newTagStr += '		<h1 class="stitle"><a href="javascript:tlstdescopen();" title="행정상태 도움말 새창으로 열림"><span class="{LST_CSS}">{LST}</span></a> <img style="margin: -3px 0 -7px 6px; width:20px; height:20px;" src="{TM5_SRC}" title="{TM5_TITLE}"/> <a href="{VIEW_LINK}" title="새창으로 열림">{TTL}</a></h1>' ;
				newTagStr += '		<div class="btn_doc">' ;
								if (jQuery(this).find("CA").text() == "Y") {
						                  newTagStr += ' <a href="{VIEW_LINK_CA}" title="공존동의상표 새창으로 열림"><img src="/kportal/images/button/btn_ca.png" alt="공존동의" /></a>' ;
						        }
                                if (jQuery(this).find("CHECKRGFLAG").text() == "Y") {
                                        newTagStr += '<a href="{VIEW_LINK_RGST2}" title="등록사항 새창으로 열림"><img src="/kportal/images/button/btn_checkReg.gif" alt="등록사항" /></a>' ;
                                }
                                
                                if (jQuery(this).find("JMFLAG").text() == "Y") {
                                        newTagStr += '<a href="{VIEW_LINK_JUGEMENT}" title="심판사항 새창으로 열림"><img src="/kportal/images/button/btn_judgment.gif" alt="심판사항" /></a>' ;
                                }
                                
                                if (jQuery(this).find("DMPFLAG").text() == "Y") {
                                        newTagStr += '<a href="{FULLTEXT_VIEW}" title="공보 새창으로 열림"><img src="/kportal/images/button/btn_kor.gif" alt="공보" /></a>' ;
                                }
                                
                                newTagStr += '	        </div>' ;
				newTagStr += '	</div>' ;
				newTagStr += '	<div class="search_basic_info">' ;
				newTagStr += '		<ul class="noimg_list">' ;
				newTagStr += '			<li class="left_width"><span>상품분류:</span> <span class="point01">{PRC}</span></li>' ;
				newTagStr += '			<li class="right_width letter1"><span>출원인 :</span> <font title="{APNM}">{APNM}</font></li>' ;
				
                                //국제출원번호(MN)이 있으면 MN 으로 보여주고
                                if (jQuery(this).find("MN").text() != "") {
                                        newTagStr += '		<li class="left_width"><span>출원(국제등록)번호 :</span> <a href="{VIEW_LINK}" title="새창으로 열림"><span class="point01">{MN}</span></a></li>' ;
                                }
                                //국제출원번호(MN)이 없으면 ANN 출원번호로 보여줌
                                else{
                                        newTagStr += '		<li class="left_width"><span>출원(국제등록)번호 :</span> <a href="{VIEW_LINK}" title="새창으로 열림"><span class="point01">{ANN}</span></a></li>' ;
                                }
                                
                                //국제출원일자(MD)이 있으면 MD으로 보여주고
                                if (jQuery(this).find("MD").text() != "") {
                                        newTagStr += '		<li class="right_width"><span>출원(국제등록)일자 :</span> {MD}</li>' ;
                                }
                                //국제출원일자(MD)이 없으면 AD 출원일자로 보여줌
                                else{
                                        newTagStr += '		<li class="right_width"><span>출원(국제등록)일자 :</span> {AD}</li>' ;
                                }

                                //국제출원번호(MN)이 있으면 등록번호를 안보이도록 함
                                if (jQuery(this).find("MN").text() != "") {
                                        newTagStr += '		<li class="left_width"><span>등록번호 :</span></li>' ;
                                }
                                //국제출원번호(MN)이 없으면 등록번호를 보여줌
                                else{
                                        if ((jQuery(this).find("RNN").text() == "") || (jQuery(this).find("RNN").text() == " ")) {
                                            newTagStr += '	<li class="left_width"><span>등록번호 :</span></li>' ;
                                        }
                                        else{
                                            newTagStr += '	<li class="left_width"><span>등록번호 :</span> <a href="{VIEW_LINK_RGST}" title="새창으로 열림"><span class="point01">{RNN}</span></a></li>' ;
                                        }
                                }
				
                                newTagStr += '			<li class="right_width"><span>등록일자 :</span> {RD}</li>' ;
				newTagStr += '			<li class="left_width"><span>출원공고번호 :</span> {PNN}</li>' ;
				newTagStr += '			<li class="right_width"><span>출원공고일자 :</span> {PD}</li>' ;
				newTagStr += '			<li class="left_width"><span>도형코드 :</span> <span class="point01">{DRC}</span></li>' ;
                                newTagStr += '			<li class="right_width"><span>대리인 :</span> <font title="{AGNM}">{AGNM}</font></li>' ;
				newTagStr += '		</ul>' ;
				newTagStr += '	</div>' ;
				newTagStr += '</article>' ;


			} else {
			
				newTagStr += '<article>' ;
				newTagStr += '	<div class="search_section_title">' ;
				//newTagStr += '		<span class="float_left"><input type="checkbox" id="search_extend" /></span>' ;
				newTagStr += '		<h1 class="stitle"><a href="javascript:tlstdescopen();" title="행정상태 도움말 새창으로 열림"><span class="{LST_CSS}">{LST}</span></a> <img style="margin: -3px 0 -7px 6px; width:20px; height:20px;" src="{TM5_SRC}" title="{TM5_TITLE}" /> <a href="{VIEW_LINK}" title="새창으로 열림">{TTL}</a></h1>' ;
				newTagStr += '		<div class="btn_doc">' ;
								if (jQuery(this).find("CA").text() == "Y") {
						                  newTagStr += ' <a href="{VIEW_LINK_CA}" title="공존동의상표 새창으로 열림"><img src="/kportal/images/button/btn_ca.png" alt="공존동의" /></a>' ;
						        }
                                if (jQuery(this).find("CHECKRGFLAG").text() == "Y") {
                                        newTagStr += '<a href="{VIEW_LINK_RGST2}" title="등록사항 새창으로 열림"><img src="/kportal/images/button/btn_checkReg.gif" alt="등록사항" /></a>' ;
                                }
                                
                                if (jQuery(this).find("JMFLAG").text() == "Y") {
                                        newTagStr += '<a href="{VIEW_LINK_JUGEMENT}" title="심판사항 새창으로 열림"><img src="/kportal/images/button/btn_judgment.gif" alt="심판사항" /></a>' ;
                                }
                                
                                if (jQuery(this).find("DMPFLAG").text() == "Y") {
                                        newTagStr += '<a href="{FULLTEXT_VIEW}" title="공보 새창으로 열림"><img src="/kportal/images/button/btn_kor.gif" alt="공보" /></a>' ;
                                }
                                
				newTagStr += '	        </div>' ;
                                newTagStr += '	</div>' ;
				newTagStr += '	<div class="search_basic_info">' ;
                                        
                                if (jQuery(this).find("IMG").find("alt").text() == "이미지 없음") {
                                        newTagStr += '		<div class="thumb"><img src="{IMG_SRC}" width="100" height="100" alt="새창으로 열림" /></div>' ;
                                }
                                else{
                                        newTagStr += '		<div class="thumb"><a href="{LINK_IMG_VIEW}" title="새창으로 열림"><img src="{IMG_SRC}" width="100" height="100" alt="새창으로 열림" /></a></div>' ;
                                }
                                        
				newTagStr += '		<ul class="search_info_list">' ;
				newTagStr += '			<li class="left_width"><span>상품분류:</span> <span class="point01">{PRC}</span></li>' ;
				newTagStr += '			<li class="right_width letter1"><span>출원인 :</span> <font title="{APNM}">{APNM}</font></li>' ;
				
				
                                //국제출원번호(MN)이 있으면 MN 으로 보여주고
                                if (jQuery(this).find("MN").text() != "") {
                                        newTagStr += '		<li class="left_width"><span>출원(국제등록)번호 :</span> <a href="{VIEW_LINK}" title="새창으로 열림"><span class="point01">{MN}</span></a></li>' ;
                                }
                                //국제출원번호(MN)이 없으면 ANN 출원번호로 보여줌
                                else{
                                        newTagStr += '		<li class="left_width"><span>출원(국제등록)번호 :</span> <a href="{VIEW_LINK}" title="새창으로 열림"><span class="point01">{ANN}</span></a></li>' ;
                                }
                                
                                //국제출원일자(MD)이 있으면 MD으로 보여주고
                                if (jQuery(this).find("MD").text() != "") {
                                        newTagStr += '		<li class="right_width"><span>출원(국제등록)일자 :</span> {MD}</li>' ;
                                }
                                //국제출원일자(MD)이 없으면 AD 출원일자로 보여줌
                                else{
                                        newTagStr += '		<li class="right_width"><span>출원(국제등록)일자 :</span> {AD}</li>' ;
                                }

                                //국제출원번호(MN)이 있으면 등록번호를 안보이도록 함
                                if (jQuery(this).find("MN").text() != "") {
                                        newTagStr += '		<li class="left_width"><span>등록번호 :</span></li>' ;
                                }
                                //국제출원번호(MN)이 없으면 등록번호를 보여줌
                                else{
                                        if ((jQuery(this).find("RNN").text() == "") || (jQuery(this).find("RNN").text() == " ")) {
                                            newTagStr += '	<li class="left_width"><span>등록번호 :</span></li>' ;
                                        }
                                        else{
                                            newTagStr += '	<li class="left_width"><span>등록번호 :</span> <a href="{VIEW_LINK_RGST}" title="새창으로 열림"><span class="point01">{RNN}</span></a></li>' ;
                                        }
                                }
				
				newTagStr += '			<li class="right_width"><span>등록일자 :</span> {RD}</li>' ;
				newTagStr += '			<li class="left_width"><span>출원공고번호 :</span> {PNN}</li>' ;
				newTagStr += '			<li class="right_width"><span>출원공고일자 :</span> {PD}</li>' ;
				newTagStr += '			<li class="left_width"><span>도형코드 :</span> <span class="point01">{DRC}</span></li>' ;
                                newTagStr += '			<li class="right_width"><span>대리인 :</span> <font title="{AGNM}">{AGNM}</font></li>' ;
				newTagStr += '		</ul>' ;
				newTagStr += '	</div>' ;
				newTagStr += '</article>' ;

			}

			newTagStr = newTagStr.replace(/{VIEW_LINK}/g, "javascript:GoBibliography('TM', '{ANN}', '{ARTICLE_IDX}', 'A', '', 'View01')") ;
            newTagStr = newTagStr.replace(/{FULLTEXT_VIEW}/g, "javascript:GoBibliography('TM', '{ANN}', '{ARTICLE_IDX}', 'F', '', 'View02')") ;
            newTagStr = newTagStr.replace(/{VIEW_LINK_RGST}/g, "javascript:GoBibliography('TM', '{ANN}', '{ARTICLE_IDX}', 'A', '', 'View04')") ;
            newTagStr = newTagStr.replace(/{VIEW_LINK_RGST2}/g, "javascript:GoBibliography('TM', '{ANN}', '{ARTICLE_IDX}', 'R', '', 'View04')") ;
            newTagStr = newTagStr.replace(/{VIEW_LINK_JUGEMENT}/g, "javascript:GoBibliography('TM', '{ANN}', '{ARTICLE_IDX}', 'F', '', 'View05')") ;
            
            newTagStr = newTagStr.replace(/{VIEW_LINK_CA}/g, "javascript:GoBibliography('TM', '{ANN}', '{ARTICLE_IDX}', 'F', '', 'View01sub07')") ;
			
			var cNak = jQuery(this).find("NAK").text();
			if (cNak == "SOUNDS" || cNak == "sounds") {
				newTagStr = newTagStr.replace(/{LINK_IMG_VIEW}/g, "javascript:downSound('{ANN}', 'SOUNDS')");
			} else if (cNak == "FRAGRE" || cNak == "fragre") {
				newTagStr = newTagStr.replace(/{LINK_IMG_VIEW}/g, "javascript:downSound('{ANN}', 'FRAGRE')");
			} else {
				newTagStr = newTagStr.replace(/{LINK_IMG_VIEW}/g, "javascript:GoBigImageTM('{ANN}','{IMG_NM}')") ;
			}
			
			newTagStr = newTagStr.replace(/{TYPE}/g, "TM") ;
			newTagStr = newTagStr.replace(/{PAGE}/g, jQuery(xml).find("search").find("page").find("searchPage").text()) ;
			newTagStr = newTagStr.replace(/{ARTICLE_IDX}/g, articleIdx) ;

			var KTN = jQuery(this).find("KTN").text() ;
			if (KTN == "" || KTN == "&nbsp;") KTN = "" ;
			var ETN = jQuery(this).find("ETN").text() ;
			if (ETN == "" || ETN == "&nbsp;") ETN = "" ;
			var TTL = "" ;
			if (KTN == "") {
				TTL = ETN ;
			} else {
				if (ETN == "") {
					TTL = KTN ;
				} else {
					TTL = KTN + " " + ETN ;
				}
			}

			if (TTL == "") {
				TTL = "(상표명 정보 없음)" ;
			}

			var LAS = jQuery(this).find("LAS").text() ;
			if (jQuery(this).find("LST").text() == "") {
				LAS = "" ;
			}

			switch (LAS) {
				case "A" :
					newTagStr = newTagStr.replace(/{LST_CSS}/g, "box_small_a") ; break ;
				case "B" :
					newTagStr = newTagStr.replace(/{LST_CSS}/g, "box_small_b") ; break ;
				case "J" :
					newTagStr = newTagStr.replace(/{LST_CSS}/g, "box_small_j") ; break ;
				case "R" :
					newTagStr = newTagStr.replace(/{LST_CSS}/g, "box_small_r") ; break ;
				case "F" :
					newTagStr = newTagStr.replace(/{LST_CSS}/g, "box_small_f") ; break ;
				case "I" :
					newTagStr = newTagStr.replace(/{LST_CSS}/g, "box_small_i") ; break ;
				case "C" :
					newTagStr = newTagStr.replace(/{LST_CSS}/g, "box_small_c") ; break ;
				case "G" :
					newTagStr = newTagStr.replace(/{LST_CSS}/g, "box_small_g") ; break ;
				default :
					newTagStr = newTagStr.replace(/{LST_CSS}/g, "") ; break ;
			}

			var IMP = jQuery(this).find("IMP").text() ;
			if (trim(IMP) == "" || IMP == "&nbsp;" || IMP == "NULL") {
				IMP = "null" ;
			}
			newTagStr = newTagStr.replace(/{IMP}/g, IMP) ;
			newTagStr = newTagStr.replace(/{LST}/g, jQuery(this).find("LST").text()) ;
			newTagStr = newTagStr.replace(/{KTN}/g, KTN) ;
			newTagStr = newTagStr.replace(/{ETN}/g, ETN) ;
			newTagStr = newTagStr.replace(/{TTL}/g, TTL) ;
			newTagStr = newTagStr.replace(/{IMG_SRC}/g, jQuery(this).find("IMG").find("src").text()) ;
			newTagStr = newTagStr.replace(/{IMG_ALT}/g, "새창으로 열림") ;
			newTagStr = newTagStr.replace(/{IMG_NM}/g, jQuery(this).find("IMG").find("nm").text()) ;
			newTagStr = newTagStr.replace(/{PRC}/g, jQuery(this).find("PRC").text()) ;
			newTagStr = newTagStr.replace(/{APNM}/g, jQuery(this).find("APNM").text()) ;
			newTagStr = newTagStr.replace(/{ANN}/g, jQuery(this).find("ANN").text()) ;
                        newTagStr = newTagStr.replace(/{AD}/g, dateFormat(jQuery(this).find("AD").text(), "yyyy.mm.dd")) ;
                        newTagStr = newTagStr.replace(/{MN}/g, jQuery(this).find("MN").text()) ;
                        newTagStr = newTagStr.replace(/{MD}/g, dateFormat(jQuery(this).find("MD").text(), "yyyy.mm.dd")) ;
			newTagStr = newTagStr.replace(/{RNN}/g, jQuery(this).find("RNN").text()) ;
			newTagStr = newTagStr.replace(/{RD}/g, dateFormat(jQuery(this).find("RD").text(), "yyyy.mm.dd")) ;
			newTagStr = newTagStr.replace(/{PNN}/g, jQuery(this).find("PNN").text()) ;
			newTagStr = newTagStr.replace(/{PD}/g, dateFormat(jQuery(this).find("PD").text(), "yyyy.mm.dd")) ;
			newTagStr = newTagStr.replace(/{DRC}/g, jQuery(this).find("DRC").text()) ;
                        newTagStr = newTagStr.replace(/{AGNM}/g, jQuery(this).find("AGNM").text()) ;
                        newTagStr = newTagStr.replace(/{TM5_SRC}/g, jQuery(this).find("TM5").find("src").text()) ;
                        newTagStr = newTagStr.replace(/{TM5_TITLE}/g, jQuery(this).find("TM5").find("title").text()) ;

			var newTag = jQuery(newTagStr) ;
			$("#trademarkResultList").append(newTag) ;

			articleIdx++ ;
		}

	) ;

}

function setTrademarkResultCountBoard(V) {
	if (V == void 0 || V == null) {
		jQuery("#trademarkResultCountBoard").empty() ;
	} else {
		jQuery("#trademarkResultCountBoard").html(V) ;
	}
}

function setTrademarkResultViewMode() {
	setTrademarkResultList(trademarkResultXmlData) ;
}

function changeTrademarkResultViewMode() {
	trademarkLoadingDisplay = true ;
	showTrademarkLoading() ;
	window.setTimeout(setTrademarkResultViewMode, 500) ;
}

function setTrademarkResultList(xml) {

	trademarkLoadingDisplay = false ;
	hideTrademarkLoading() ;

	jQuery("#trademarkResultList").empty() ;

	jQuery("#trademarkResultMore").hide() ;

	var searchResultCount = parseInt(jQuery(xml).find("search").find("searchFound").text()) ;

	if (searchResultCount > 0) {

		addTrademarkResult(xml) ;

		if (parseInt(jQuery(xml).find("search").find("searchFound").text()) > 0) {

			jQuery("#trademarkQueryText").val(jQuery(xml).find("search").find("searchKeyword").text()) ;
			jQuery("#trademarkExpression").val(jQuery(xml).find("search").find("searchExpression").text()) ;

			jQuery("#trademarkSearchInTrans").val(jQuery(xml).find("search").find("searchExtend").text()) ;

			jQuery("#trademarkResultMore").show() ;
		}

	} else {
		printTrademarkSearchException(jQuery(xml).find("message").text()) ;
	}

}

function setTrademarkResult(xml) {

	if (jQuery(xml).find("flag").text() == "SUCCESS") {

		setTrademarkResultCountBoard("<em class=\"txt_bold\">" + numberFormat(jQuery(xml).find("search").find("searchFound").text()) + "</em>건 검색") ;

		var searchResultCount = parseInt(jQuery(xml).find("search").find("searchFound").text()) ;

		setTrademarkSearchResultCount(searchResultCount) ;

		setTrademarkResultList(xml) ;

	} else {

		trademarkLoadingDisplay = false ;
		hideTrademarkLoading() ;

		jQuery("#trademarkResultList").empty() ;
		jQuery("#trademarkResultMore").hide() ;

		setTrademarkSearchResultCount(-1) ;
		printTrademarkSearchException(jQuery(xml).find("message").text()) ;

	}

}

function printTrademarkSearchException(V) {

	var newTagStr = "<li>" ;
	newTagStr += "<div class=\"search_section_title\">" ;
	newTagStr += "<h3>" + V + "</h3>" ;
	newTagStr += "</div>" ;
	newTagStr += "</li>" ;

	setTrademarkResultCountBoard(null) ;

	jQuery("#trademarkResultList").empty() ;
	jQuery("#trademarkResultMore").hide() ;

	$("#trademarkResultList").append(newTagStr) ;

}

var trademarkFadeTimerId = null ;
var trademarkFadeValue = 0 ;
var trademarkLoadingDisplay = true ;
function showTrademarkLoading() {
	if (trademarkLoadingDisplay) {

		if (isPageError) {
			if (trademarkFadeTimerId) {
				window.clearInterval(trademarkFadeTimerId) ;
				trademarkFadeTimerId = null ;
				trademarkFadeValue = 0 ;
			}
			jQuery("#trademarkResultLoadingBoard").width(jQuery("#trademarkResultList").width()).height(jQuery("#trademarkResultList").height()) ;
			jQuery("#trademarkResultLoadingBoard").css(
							{
								"margin-top" : jQuery("#trademarkTitle").outerHeight(true)
							}
					) ;

			jQuery("#trademarkResultLoading").css(
							{
								"margin-top": ((jQuery("#trademarkResultList").height() / 2) - (jQuery("#trademarkResultLoading").height() / 2)) + jQuery("#trademarkTitle").outerHeight(true)
								, "margin-left": parseInt((jQuery("#trademarkResultList").width() / 2) - (jQuery("#trademarkResultLoading").width() / 2))
							}
					) ;
			jQuery("#trademarkResultLoading").show() ;
		} else {

			if (trademarkFadeTimerId == void 0) {
				trademarkFadeTimerId = window.setInterval(showTrademarkLoading, 10) ;
				jQuery("#trademarkResultLoadingBoard").width(jQuery("#trademarkResultList").width()).height(jQuery("#trademarkResultList").height()) ;
				jQuery("#trademarkResultLoadingBoard").css(
								{
									"margin-top" : jQuery("#trademarkTitle").outerHeight(true)
								}
						) ;

				jQuery("#trademarkResultLoading").css(
								{
									"margin-top": ((jQuery("#trademarkResultList").height() / 2) - (jQuery("#trademarkResultLoading").height() / 2)) + jQuery("#trademarkTitle").outerHeight(true)
									, "margin-left": parseInt((jQuery("#trademarkResultList").width() / 2) - (jQuery("#trademarkResultLoading").width() / 2))
								}
						) ;

			}
			jQuery("#trademarkResultLoadingBoard").fadeTo(0, trademarkFadeValue * 0.08) ;
			if (trademarkFadeValue >= 10) {
				window.clearInterval(trademarkFadeTimerId) ;
				trademarkFadeTimerId = null ;
				jQuery("#trademarkResultLoading").show() ;
				trademarkFadeValue = 0 ;
			} else {
				trademarkFadeValue++ ;
			}
		}
	} else {
		if (trademarkFadeTimerId) {
			window.clearInterval(trademarkFadeTimerId) ;
			trademarkFadeTimerId = null ;
			trademarkFadeValue = 0 ;
		}
		hideTrademarkLoading() ;
	}
}

function hideTrademarkLoading() {
	jQuery("#trademarkResultLoading").fadeOut(1000) ;
	jQuery("#trademarkResultLoadingBoard").fadeOut(1000) ;
	jQuery("#trademarkResultLoadingBoard").width(0).height(0) ;
	jQuery("#trademarkResultLoading").hide() ;
	jQuery("#trademarkResultLoadingBoard").hide() ;
}

function getTrademarkSearchResult(keyword, expression) {

	trademarkResultXmlData = null ;

	jQuery("#resultTrademark").show() ;
	trademarkLoadingDisplay = true ;
	showTrademarkLoading() ;

	setTrademarkResultCountBoard("검색 중입니다.") ;

	setTrademarkSearchResultCount(-1) ;

	jQuery.ajax({
		type : "POST" ,
		dataType : "xml" ,
		url : "/kportal/resulta.do" ,
		data : {
				next : "trademarkList"
				, FROM : "SEARCH"
				, searchInTransKorToEng : ((isSearchExtends) ? "Y" : "N")
				, searchInTransEngToKor : ((isSearchExtends) ? "Y" : "N")
				, row : "3"
				, queryText : keyword
				, expression : expression
		} ,
		success : function(xml, textStatus) {
			trademarkResultXmlData = xml ;
			setTrademarkResult(xml) ;
		} ,
		error : function(xhr, textStatus) {
			trademarkLoadingDisplay = false ;
			hideTrademarkLoading() ;
			printTrademarkSearchException("검색 도중 오류가 발생하였습니다.[" + xhr.status + "]") ;
		}
	}) ;
}


</script>



<form name="frnUSMoreFrm" id="frnUSMoreFrm" method="post">
				<section id="resultFrnUS" class="search_section">
					<div id="frnUSResultLoadingBoard"></div>
					<div id="frnUSResultLoading"><img src="/kportal/images/common/loading_foreign.gif" alt="해외특허 검색결과를 불러오고 있습니다." /></div>
					<h2 id="frnUSTitle" class="total_title">[미국] <button type="submit" id="moreFrnUSResult2" ><span id="frnUSResultCountBoard"><em class="txt_bold"></em>건 검색</span></button></h2>
					<div id="frnUSResultList">
						<div class="search_blank"></div>
					</div>
                                        <input type="hidden" name="next" value="frnUS" />
                                        <input type="hidden" id="frnUSQueryText" name="queryText" value="" />
                                        <input type="hidden" id="frnUSExpression" name="expression" value="" />
                                        <input type="hidden" id="frnUSSearchInTrans" name="searchInTrans" value="" />
                                        <input type="hidden" name="config" value="G1111111111111111111111S110001000000000000" />
                                        <input type="hidden" name="numPerPage" value="30" />
                                        <input type="hidden" name="currentPage" value="1" />
                                        <input type="hidden" name="sortField1" value="Score" />
                                        <input type="hidden" name="sortState1" value="Desc" />
                                        <input type="hidden" name="nowTab" value="US_T.col" />
                                        <input type="hidden" name="collectionValues" value="US_T.col" />
					<p id="frnUSResultMore" class="total_more">
						<span class="more_plus"><button type="submit" id="goFrnUSResult" >해외특허(미국)<span style="color:#00a13a"> 더보기</span></button></span>
						<span class="more"><button type="submit" id="moreFrnUSResult" >통합검색<span style="color:#00a13a"> 더보기</span></button></span>
					</p>
                                </section>
</form>
				
<script type="text/javascript">

jQuery("#moreFrnUSResult").click(
	function(evt) {
		jQuery("#frnUSMoreFrm").prop("action", "/kportal/search/search_frn_us.do") ;
	}
) ;
jQuery("#moreFrnUSResult2").click(
	function(evt) {
		jQuery("#frnUSMoreFrm").prop("action", "/kportal/search/search_frn_us.do") ;
	}
) ;
jQuery("#goFrnUSResult").click(
	function(evt) {
		jQuery("#frnUSMoreFrm").prop("action", "https://www.kipris.or.kr/abpat/searchLogina.do?next=MainSearch") ;
	}
) ;

var frnUSResultXmlData = null ;

function addFrnUSResult(xml) {

	var articleIdx = 0 ;
	jQuery(xml).find("search").find("articles").find("article").each(
		function(idx) {

			var newTagStr = "" ;

			if (resultViewMode == "TEXT") {

				newTagStr += '<article>' ;
				newTagStr += '	<div class="search_section_title">' ;
				//newTagStr += '		<span class="float_left"><input type="checkbox" id="search_extend" /></span>' ;
				newTagStr += '		<h1 class="stitle"><span class="icon_flag"><img src="/kportal/images/flag/icon_us.gif" alt="US(미국)" /></span><a href="{VIEW_LINK}" title="새창으로 열림">{TL}</a></h1>' ;
				newTagStr += '		<div class="btn_doc">' ;

                                if (jQuery(this).find("examinedTextFg").text() == "Y") {
                                        newTagStr += '	<a href="{LINK_FULL_TEXT}" title="공보 새창으로 열림"><img src="/kportal/images/button/btn_kor.gif" alt="공보" /></a>' ;
                                }
                                
                                newTagStr += '	        </div>' ;
				newTagStr += '	</div>' ;
				newTagStr += '	<div class="search_basic_info">' ;
				newTagStr += '		<ul class="noimg_list">' ;
				newTagStr += '			<li class="left_width"><span>IPC :</span> <span class="point01">{IPC}</span></li>' ;
				newTagStr += '			<li class="right_width"><span>CPC :</span> <span class="point01">{CPC}</span></li>' ;
                                newTagStr += '			<li class="left_width"><span>출원번호 :</span> <a href="{VIEW_LINK}" title="새창으로 열림">{AN}</a></li>' ;
				newTagStr += '			<li class="right_width"><span>출원일자 :</span> {AD}</li>' ;
				newTagStr += '			<li class="left_width"><span>등록번호 :</span> {GN}</li>' ;
				newTagStr += '			<li class="right_width"><span>등록일자 :</span> {GD}</li>' ;
				newTagStr += '			<li class="left_width"><span>공개번호 :</span> {OPN}</li>' ;
				newTagStr += '			<li class="right_width"><span>공개일자 :</span> {OPD}</li>' ;
				newTagStr += '			<li class="left_width"><span>공보번호 :</span> {PN}</li>' ;
				newTagStr += '			<li class="right_width"><span>공보일자 :</span> {PD}</li>' ;
                                newTagStr += '			<li class="left_width"><span>출원인 :</span> <font title="{AP}">{AP}</font></li>' ;
				newTagStr += '		</ul>' ;
				newTagStr += '		<div class="search_detail_content">' ;
				newTagStr += '			<div class="search_txt">' ;
				newTagStr += '				<span class="btn_abstract"><img src="/kportal/images/button/btn_abstract.gif" alt="요약" /></span>' ;
				newTagStr += '				{AB}' ;
				newTagStr += '			</div>' ;
				newTagStr += '		</div>' ;
				newTagStr += '	</div>' ;
				newTagStr += '</article>' ;

			} else {

				newTagStr += '<article>' ;
				newTagStr += '	<div class="search_section_title">' ;
				newTagStr += '		<h1 class="stitle"><span class="icon_flag"><img src="/kportal/images/flag/icon_us.gif" alt="US(미국)" /></span><a href="{VIEW_LINK}" title="새창으로 열림"> {TL} </a></h1>' ; 
				newTagStr += '		<div class="btn_doc">' ;

                                if (jQuery(this).find("examinedTextFg").text() == "Y") {
                                        newTagStr += '	<a href="{LINK_FULL_TEXT}" title="공보 새창으로 열림"><img src="/kportal/images/button/btn_kor.gif" alt="공보" /></a>' ;
                                }
                                
                                newTagStr += '	        </div>' ;
				newTagStr += '	</div>' ;
				newTagStr += '	<div class="search_basic_info">' ;
                                newTagStr += '		<div class="thumb"><a href="{VIEW_IMAGE_LINK}" title="새창으로 열림"><img src="{IMG_SRC}" width="100" height="100" alt="{IMG_ALT}" /></a></div>' ;
				//newTagStr += '		<ul class="search_info_list">' ;
                                newTagStr += '		<ul class="search_info_list">' ;
				newTagStr += '			<li class="left_width"><span>IPC :</span> <span class="point01">{IPC}</span></li>' ;
				newTagStr += '			<li class="right_width"><span>CPC :</span> <span class="point01">{CPC}</span></li>' ;
				newTagStr += '			<li class="left_width"><span>출원번호 :</span> <a href="{VIEW_LINK}" title="새창으로 열림">{AN}</a></li>' ;
				newTagStr += '			<li class="right_width"><span>출원일자 :</span> {AD}</li>' ;
				newTagStr += '			<li class="left_width"><span>등록번호 :</span> {GN}</li>' ;
				newTagStr += '			<li class="right_width"><span>등록일자 :</span> {GD}</li>' ;
				newTagStr += '			<li class="left_width"><span>공개번호 :</span> {OPN}</li>' ;
				newTagStr += '			<li class="right_width"><span>공개일자 :</span> {OPD}</li>' ;
				newTagStr += '			<li class="left_width"><span>공보번호 :</span> {PN}</li>' ;
				newTagStr += '			<li class="right_width"><span>공보일자 :</span> {PD}</li>' ;
				newTagStr += '			<li class="left_width"><span>출원인 :</span> <font title="{AP}">{AP}</font></li>' ;
                                newTagStr += '		</ul>' ;
				newTagStr += '	</div>' ;
				newTagStr += '</article>' ;

			}

			var AB = jQuery(this).find("AB").text() ;
			if (AB == "내용 없음" || AB == "내용없음" || AB == "내용 없음.") { AB = "" ; }
			if (AB == "") {
				AB = '<span class="no_abstract">내용 없음</span>' ;
			}

			newTagStr = newTagStr.replace(/{VIEW_LINK}/g, "javascript:viewForeignPatent('{VdkVgwKey}', '{COLLECTION}', '{PAGE}', '{COUNTRY}', '{ARTICLE_IDX}')") ;
			newTagStr = newTagStr.replace(/{LINK_FULL_TEXT}/g, "javascript:openDetailAbpat('{VdkVgwKey}', '{COLLECTION}', '{PAGE}', '{COUNTRY}', '{ARTICLE_IDX}')") ;

			newTagStr = newTagStr.replace(/{VdkVgwKey}/g, jQuery(this).find("VdkVgwKey").text()) ;
			newTagStr = newTagStr.replace(/{COLLECTION}/g, "US_T.col") ;
			newTagStr = newTagStr.replace(/{PAGE}/g, jQuery(xml).find("search").find("page").find("searchPage").text()) ;
			newTagStr = newTagStr.replace(/{COUNTRY}/g, jQuery(this).find("CC").text()) ;
			newTagStr = newTagStr.replace(/{ARTICLE_IDX}/g, articleIdx) ;
			newTagStr = newTagStr.replace(/{TL}/g, jQuery(this).find("TL").text()) ;
			newTagStr = newTagStr.replace(/{IPC}/g, jQuery(this).find("IPC").text()) ;
                        newTagStr = newTagStr.replace(/{CPC}/g, jQuery(this).find("CPC").text()) ;
			newTagStr = newTagStr.replace(/{AP}/g, jQuery(this).find("AP").text()) ;
			newTagStr = newTagStr.replace(/{AN}/g, jQuery(this).find("AN").text()) ;
			newTagStr = newTagStr.replace(/{AD}/g, dateFormat(jQuery(this).find("AD").text(), "yyyy.mm.dd")) ;
			newTagStr = newTagStr.replace(/{GN}/g, jQuery(this).find("GN").text()) ;
			newTagStr = newTagStr.replace(/{GD}/g, dateFormat(jQuery(this).find("GD").text(), "yyyy.mm.dd")) ;
			newTagStr = newTagStr.replace(/{OPN}/g, jQuery(this).find("OPN").text()) ;
			newTagStr = newTagStr.replace(/{OPD}/g, dateFormat(jQuery(this).find("OPD").text(), "yyyy.mm.dd")) ;
			newTagStr = newTagStr.replace(/{PN}/g, jQuery(this).find("PN").text()) ;
			newTagStr = newTagStr.replace(/{PD}/g, dateFormat(jQuery(this).find("PD").text(), "yyyy.mm.dd")) ;
                        newTagStr = newTagStr.replace(/{IMG_SRC}/g, jQuery(this).find("IMG").find("src").text()) ;
                        newTagStr = newTagStr.replace(/{IMG_ALT}/g, jQuery(this).find("IMG").find("alt").text()) ;
                        newTagStr = newTagStr.replace(/{VIEW_IMAGE_LINK}/g, "javascript:OpenFrontDrawPopABPAT('"+jQuery(this).find("VdkVgwKey").text().replace(",","")+"','US')");
			newTagStr = newTagStr.replace(/{AB}/g, AB) ;

			var newTag = jQuery(newTagStr) ;
			$("#frnUSResultList").append(newTag) ;

			articleIdx++ ;
		}
	) ;
}

function setFrnUSResultCountBoard(V) {
	if (V == void 0 || V == null) {
		jQuery("#frnUSResultCountBoard").empty() ;
	} else {
		jQuery("#frnUSResultCountBoard").html(V) ;
	}
}

function setFrnUSResultViewMode() {
	setFrnUSResultList(frnUSResultXmlData) ;
}

function changeFrnUSResultViewMode() {
	frnUSLoadingDisplay = true ;
	showFrnUSLoading() ;
	window.setTimeout(setFrnUSResultViewMode, 500) ;
}

function setFrnUSResultList(xml) {

	frnUSLoadingDisplay = false ;
	hideFrnUSLoading() ;

	jQuery("#frnUSResultList").empty() ;

	jQuery("#frnUSResultMore").hide() ;

	var searchResultCount = parseInt(jQuery(xml).find("search").find("searchFound").text()) ;

	if (searchResultCount > 0) {

		addFrnUSResult(xml) ;

		if (parseInt(jQuery(xml).find("search").find("searchFound").text()) > 0) {

			jQuery("#frnUSQueryText").val(jQuery(xml).find("search").find("searchKeyword").text()) ;
			jQuery("#frnUSExpression").val(jQuery(xml).find("search").find("searchExpression").text()) ;

			jQuery("#frnUSSearchInTrans").val(jQuery(xml).find("search").find("searchExtend").text()) ;

			jQuery("#frnUSResultMore").show() ;
		}

	} else {
		printFrnUSSearchException(jQuery(xml).find("message").text()) ;
	}

}

function setFrnUSResult(xml) {

	if (jQuery(xml).find("flag").text() == "SUCCESS") {

		setFrnUSResultCountBoard("<em class=\"txt_bold\">" + numberFormat(jQuery(xml).find("search").find("searchFound").text()) + "</em>건 검색") ;

		var searchResultCount = parseInt(jQuery(xml).find("search").find("searchFound").text()) ;

		setFrnUSSearchResultCount(searchResultCount) ;

		setFrnUSResultList(xml) ;

	} else {

		frnUSLoadingDisplay = false ;
		hideFrnUSLoading() ;

		jQuery("#frnUSResultList").empty() ;
		jQuery("#frnUSResultMore").hide() ;

		setFrnUSSearchResultCount(-1) ;
		printFrnUSSearchException(jQuery(xml).find("message").text()) ;

	}

}

function printFrnUSSearchException(V) {

	var newTagStr = "<li>" ;
	newTagStr += "<div class=\"search_section_title\">" ;
	newTagStr += "<h3>" + V + "</h3>" ;
	newTagStr += "</div>" ;
	newTagStr += "</li>" ;

	setFrnUSResultCountBoard(null) ;

	jQuery("#frnUSResultList").empty() ;
	jQuery("#frnUSResultMore").hide() ;

	$("#frnUSResultList").append(newTagStr) ;

}

var frnUSFadeTimerId = null ;
var frnUSFadeValue = 0 ;
var frnUSLoadingDisplay = true ;
function showFrnUSLoading() {
	if (frnUSLoadingDisplay) {

		if (isPageError) {
			if (frnUSFadeTimerId) {
				window.clearInterval(frnUSFadeTimerId) ;
				frnUSFadeTimerId = null ;
				frnUSFadeValue = 0 ;
			}
			jQuery("#frnUSResultLoadingBoard").width(jQuery("#frnUSResultList").width()).height(jQuery("#frnUSResultList").height()) ;
			jQuery("#frnUSResultLoadingBoard").css(
							{
								"margin-top" : jQuery("#frnUSTitle").outerHeight(true)
							}
					) ;

			jQuery("#frnUSResultLoading").css(
							{
								"margin-top": ((jQuery("#frnUSResultList").height() / 2) - (jQuery("#frnUSResultLoading").height() / 2)) + jQuery("#frnUSTitle").outerHeight(true)
								, "margin-left": parseInt((jQuery("#frnUSResultList").width() / 2) - (jQuery("#frnUSResultLoading").width() / 2))
							}
					) ;
			jQuery("#frnUSResultLoading").show() ;
		} else {

			if (frnUSFadeTimerId == void 0) {
				frnUSFadeTimerId = window.setInterval(showFrnUSLoading, 10) ;
				jQuery("#frnUSResultLoadingBoard").width(jQuery("#frnUSResultList").width()).height(jQuery("#frnUSResultList").height()) ;
				jQuery("#frnUSResultLoadingBoard").css(
								{
									"margin-top" : jQuery("#frnUSTitle").outerHeight(true)
								}
						) ;

				jQuery("#frnUSResultLoading").css(
								{
									"margin-top": ((jQuery("#frnUSResultList").height() / 2) - (jQuery("#frnUSResultLoading").height() / 2)) + jQuery("#frnUSTitle").outerHeight(true)
									, "margin-left": parseInt((jQuery("#frnUSResultList").width() / 2) - (jQuery("#frnUSResultLoading").width() / 2))
								}
						) ;

			}
			jQuery("#frnUSResultLoadingBoard").fadeTo(0, frnUSFadeValue * 0.08) ;
			if (frnUSFadeValue >= 10) {
				window.clearInterval(frnUSFadeTimerId) ;
				frnUSFadeTimerId = null ;
				jQuery("#frnUSResultLoading").show() ;
				frnUSFadeValue = 0 ;
			} else {
				frnUSFadeValue++ ;
			}
		}
	} else {
		if (frnUSFadeTimerId) {
			window.clearInterval(frnUSFadeTimerId) ;
			frnUSFadeTimerId = null ;
			frnUSFadeValue = 0 ;
		}
		hideFrnUSLoading() ;
	}
}

function hideFrnUSLoading() {
	jQuery("#frnUSResultLoading").fadeOut(1000) ;
	jQuery("#frnUSResultLoadingBoard").fadeOut(1000) ;
	jQuery("#frnUSResultLoadingBoard").width(0).height(0) ;
	jQuery("#frnUSResultLoading").hide() ;
	jQuery("#frnUSResultLoadingBoard").hide() ;
}

function getFrnUSSearchResult(keyword, expression) {

	frnUSResultXmlData = null ;

	jQuery("#resultFrnUS").show() ;
	frnUSLoadingDisplay = true ;
	showFrnUSLoading() ;

	setFrnUSResultCountBoard("검색 중입니다.") ;

	setFrnUSSearchResultCount(-1) ;

	jQuery.ajax({
		type : "POST" ,
		dataType : "xml" ,
		url : "/kportal/resulta.do" ,
		data : {
				next : "frnUSList"
				, FROM : "SEARCH"
				, searchInTransKorToEng : ((isSearchExtends) ? "Y" : "N")
				, searchInTransEngToKor : ((isSearchExtends) ? "Y" : "N")
				, row : "3"
				, queryText : keyword
				, expression : expression
		} ,
		success : function(xml, textStatus) {
			frnUSResultXmlData = xml ;
			setFrnUSResult(xml) ;
		} ,
		error : function(xhr, textStatus) {
			frnUSLoadingDisplay = false ;
			hideFrnUSLoading() ;
			printFrnUSSearchException("검색 도중 오류가 발생하였습니다.[" + xhr.status + "]") ;
		}
	}) ;
}


</script>



<form name="frnEUMoreFrm" id="frnEUMoreFrm" method="post">
				<section id="resultFrnEU" class="search_section">
					<div id="frnEUResultLoadingBoard"></div>
					<div id="frnEUResultLoading"><img src="/kportal/images/common/loading_foreign.gif" alt="해외특허 검색결과를 불러오고 있습니다." /></div>
					<h2 id="frnEUTitle" class="total_title">[유럽] <button type="submit" id="moreFrnEUResult2" ><span id="frnEUResultCountBoard"><em class="txt_bold"></em>건 검색</span></button></h2>
					<div id="frnEUResultList">
						<div class="search_blank"></div>
					</div>
                                        <input type="hidden" name="next" value="frnEU" />
                                        <input type="hidden" id="frnEUQueryText" name="queryText" value="" />
                                        <input type="hidden" id="frnEUExpression" name="expression" value="" />
                                        <input type="hidden" id="frnEUSearchInTrans" name="searchInTrans" value="" />
                                        <input type="hidden" name="config" value="G1111111111111111111111S110001000000000000" />
                                        <input type="hidden" name="numPerPage" value="30" />
                                        <input type="hidden" name="currentPage" value="1" />
                                        <input type="hidden" name="sortField1" value="Score" />
                                        <input type="hidden" name="sortState1" value="Desc" />
                                        <input type="hidden" name="nowTab" value="EP_T.col" />
                                        <input type="hidden" name="collectionValues" value="EP_T.col" />
					<p id="frnEUResultMore" class="total_more">
						<span class="more_plus"><button type="submit" id="goFrnEUResult" >해외특허(유럽)<span style="color:#00a13a"> 더보기</span></button></span>
						<span class="more"><button type="submit" id="moreFrnEUResult" >통합검색<span style="color:#00a13a"> 더보기</span></button></span>
					</p>
                                </section>
</form>
				
<script type="text/javascript">

jQuery("#moreFrnEUResult").click(
	function(evt) {
		jQuery("#frnEUMoreFrm").prop("action", "/kportal/search/search_frn_eu.do") ;
	}
) ;
jQuery("#moreFrnEUResult2").click(
	function(evt) {
		jQuery("#frnEUMoreFrm").prop("action", "/kportal/search/search_frn_eu.do") ;
	}
) ;
jQuery("#goFrnEUResult").click(
	function(evt) {
		jQuery("#frnEUMoreFrm").prop("action", "https://www.kipris.or.kr/abpat/searchLogina.do?next=MainSearch") ;
	}
) ;

var frnEUResultXmlData = null ;

function addFrnEUResult(xml) {

	var articleIdx = 0 ;
	jQuery(xml).find("search").find("articles").find("article").each(
		function(idx) {

			var newTagStr = "" ;

			if (resultViewMode == "TEXT") {

				newTagStr += '<article>' ;
				newTagStr += '	<div class="search_section_title">' ;
				//newTagStr += '		<span class="float_left"><input type="checkbox" id="search_extend" /></span>' ;
				newTagStr += '		<h1 class="stitle"><span class="icon_flag"><img src="/kportal/images/flag/icon_ep.gif" alt="EP(유럽)" /></span><a href="{VIEW_LINK}" title="새창으로 열림"> {TL} </a></h1>' ; 
				newTagStr += '		<div class="btn_doc">' ;

                                if (jQuery(this).find("examinedTextFg").text() == "Y") {
                                        newTagStr += '	<a href="{LINK_FULL_TEXT}" title="공보 새창으로 열림"><img src="/kportal/images/button/btn_kor.gif" alt="공보" /></a>' ;
                                }
                                
                                newTagStr += '	        </div>' ;
				newTagStr += '	</div>' ;
				newTagStr += '	<div class="search_basic_info">' ;
				newTagStr += '		<ul class="noimg_list">' ;
				newTagStr += '			<li class="left_width"><span>IPC :</span> <span class="point01">{IPC}</span></li>' ;
				newTagStr += '			<li class="right_width"><span>CPC :</span> <span class="point01">{CPC}</span></li>' ;
				newTagStr += '			<li class="left_width"><span>출원번호 :</span> <a href="{VIEW_LINK}" title="새창으로 열림">{AN}</a></li>' ;
				newTagStr += '			<li class="right_width"><span>출원일자 :</span> {AD}</li>' ;
				newTagStr += '			<li class="left_width"><span>등록번호 :</span> {GN}</li>' ;
				newTagStr += '			<li class="right_width"><span>등록일자 :</span> {GD}</li>' ;
				newTagStr += '			<li class="left_width"><span>공개번호 :</span> {OPN}</li>' ;
				newTagStr += '			<li class="right_width"><span>공개일자 :</span> {OPD}</li>' ;
				newTagStr += '			<li class="left_width"><span>공보번호 :</span> {PN}</li>' ;
				newTagStr += '			<li class="right_width"><span>공보일자 :</span> {PD}</li>' ;
                                newTagStr += '			<li class="left_width"><span>출원인 :</span> <font title="{AP}">{AP}</font></li>' ;
				newTagStr += '		</ul>' ;
				newTagStr += '		<div class="search_detail_content">' ;
				newTagStr += '			<div class="search_txt">' ;
				newTagStr += '				<span class="btn_abstract"><img src="/kportal/images/button/btn_abstract.gif" alt="요약" /></span>' ;
				newTagStr += '				{AB}' ;
				newTagStr += '			</div>' ;
				newTagStr += '		</div>' ;
				newTagStr += '	</div>' ;
				newTagStr += '</article>' ;

			} else {

				newTagStr += '<article>' ;
				newTagStr += '	<div class="search_section_title">' ;
				newTagStr += '		<h1 class="stitle"><span class="icon_flag"><img src="/kportal/images/flag/icon_ep.gif" alt="EP(유럽)" /></span><a href="{VIEW_LINK}" title="새창으로 열림"> {TL} </a></h1>' ; 
				newTagStr += '		<div class="btn_doc">' ;

                                if (jQuery(this).find("examinedTextFg").text() == "Y") {
                                        newTagStr += '	<a href="{LINK_FULL_TEXT}" title="공보 새창으로 열림"><img src="/kportal/images/button/btn_kor.gif" alt="공보" /></a>' ;
                                }
                                
                                newTagStr += '	        </div>' ;
				newTagStr += '	</div>' ;
				newTagStr += '	<div class="search_basic_info">' ;
                                newTagStr += '		<div class="thumb"><a href="{VIEW_IMAGE_LINK}" title="새창으로 열림"><img src="{IMG_SRC}" width="100" height="100" alt="{IMG_ALT}" /></a></div>' ;
				//newTagStr += '		<ul class="search_info_list">' ;
                                newTagStr += '		<ul class="search_info_list">' ;
				newTagStr += '			<li class="left_width"><span>IPC :</span> <span class="point01">{IPC}</span></li>' ;
				newTagStr += '			<li class="right_width"><span>CPC :</span> <span class="point01">{CPC}</span></li>' ;
				newTagStr += '			<li class="left_width"><span>출원번호 :</span> <a href="{VIEW_LINK}" title="새창으로 열림">{AN}</a></li>' ;
				newTagStr += '			<li class="right_width"><span>출원일자 :</span> {AD}</li>' ;
				newTagStr += '			<li class="left_width"><span>등록번호 :</span> {GN}</li>' ;
				newTagStr += '			<li class="right_width"><span>등록일자 :</span> {GD}</li>' ;
				newTagStr += '			<li class="left_width"><span>공개번호 :</span> {OPN}</li>' ;
				newTagStr += '			<li class="right_width"><span>공개일자 :</span> {OPD}</li>' ;
				newTagStr += '			<li class="left_width"><span>공보번호 :</span> {PN}</li>' ;
				newTagStr += '			<li class="right_width"><span>공보일자 :</span> {PD}</li>' ;
                                newTagStr += '			<li class="left_width"><span>출원인 :</span> <font title="{AP}">{AP}</font></li>' ;
				newTagStr += '		</ul>' ;
				newTagStr += '	</div>' ;
				newTagStr += '</article>' ;

			}

			var AB = jQuery(this).find("AB").text() ;
			if (AB == "내용 없음" || AB == "내용없음" || AB == "내용 없음.") { AB = "" ; }
			if (AB == "") {
				AB = '<span class="no_abstract">내용 없음</span>' ;
			}

			newTagStr = newTagStr.replace(/{VIEW_LINK}/g, "javascript:viewForeignPatent('{VdkVgwKey}', '{COLLECTION}', '{PAGE}', '{COUNTRY}', '{ARTICLE_IDX}')") ;
			newTagStr = newTagStr.replace(/{LINK_FULL_TEXT}/g, "javascript:openDetailAbpat('{VdkVgwKey}', '{COLLECTION}', '{PAGE}', '{COUNTRY}', '{ARTICLE_IDX}')") ;

			newTagStr = newTagStr.replace(/{VdkVgwKey}/g, jQuery(this).find("VdkVgwKey").text()) ;
			newTagStr = newTagStr.replace(/{COLLECTION}/g, "EP_T.col") ;
			newTagStr = newTagStr.replace(/{PAGE}/g, jQuery(xml).find("search").find("page").find("searchPage").text()) ;
			newTagStr = newTagStr.replace(/{COUNTRY}/g, jQuery(this).find("CC").text()) ;
			newTagStr = newTagStr.replace(/{ARTICLE_IDX}/g, articleIdx) ;
			newTagStr = newTagStr.replace(/{TL}/g, jQuery(this).find("TL").text()) ;
			newTagStr = newTagStr.replace(/{IPC}/g, jQuery(this).find("IPC").text()) ;
                        newTagStr = newTagStr.replace(/{CPC}/g, jQuery(this).find("CPC").text()) ;
			newTagStr = newTagStr.replace(/{AP}/g, jQuery(this).find("AP").text()) ;
			newTagStr = newTagStr.replace(/{AN}/g, jQuery(this).find("AN").text()) ;
			newTagStr = newTagStr.replace(/{AD}/g, dateFormat(jQuery(this).find("AD").text(), "yyyy.mm.dd")) ;
			newTagStr = newTagStr.replace(/{GN}/g, jQuery(this).find("GN").text()) ;
			newTagStr = newTagStr.replace(/{GD}/g, dateFormat(jQuery(this).find("GD").text(), "yyyy.mm.dd")) ;
			newTagStr = newTagStr.replace(/{OPN}/g, jQuery(this).find("OPN").text()) ;
			newTagStr = newTagStr.replace(/{OPD}/g, dateFormat(jQuery(this).find("OPD").text(), "yyyy.mm.dd")) ;
			newTagStr = newTagStr.replace(/{PN}/g, jQuery(this).find("PN").text()) ;
			newTagStr = newTagStr.replace(/{PD}/g, dateFormat(jQuery(this).find("PD").text(), "yyyy.mm.dd")) ;
                        newTagStr = newTagStr.replace(/{IMG_SRC}/g, jQuery(this).find("IMG").find("src").text()) ;
                        newTagStr = newTagStr.replace(/{IMG_ALT}/g, jQuery(this).find("IMG").find("alt").text()) ;
                        newTagStr = newTagStr.replace(/{VIEW_IMAGE_LINK}/g, "javascript:OpenFrontDrawPopABPAT('"+jQuery(this).find("VdkVgwKey").text().replace(",","")+"','EP')");

			newTagStr = newTagStr.replace(/{AB}/g, AB) ;

			var newTag = jQuery(newTagStr) ;
			$("#frnEUResultList").append(newTag) ;

			articleIdx++ ;
		}
	) ;
}

function setFrnEUResultCountBoard(V) {
	if (V == void 0 || V == null) {
		jQuery("#frnEUResultCountBoard").empty() ;
	} else {
		jQuery("#frnEUResultCountBoard").html(V) ;
	}
}

function setFrnEUResultViewMode() {
	setFrnEUResultList(frnEUResultXmlData) ;
}

function changeFrnEUResultViewMode() {
	frnEULoadingDisplay = true ;
	showFrnEULoading() ;
	window.setTimeout(setFrnEUResultViewMode, 500) ;
}

function setFrnEUResultList(xml) {

	frnEULoadingDisplay = false ;
	hideFrnEULoading() ;

	jQuery("#frnEUResultList").empty() ;

	jQuery("#frnEUResultMore").hide() ;

	var searchResultCount = parseInt(jQuery(xml).find("search").find("searchFound").text()) ;

	if (searchResultCount > 0) {

		addFrnEUResult(xml) ;

		if (parseInt(jQuery(xml).find("search").find("searchFound").text()) > 0) {

			jQuery("#frnEUQueryText").val(jQuery(xml).find("search").find("searchKeyword").text()) ;
			jQuery("#frnEUExpression").val(jQuery(xml).find("search").find("searchExpression").text()) ;

			jQuery("#frnEUSearchInTrans").val(jQuery(xml).find("search").find("searchExtend").text()) ;

			jQuery("#frnEUResultMore").show() ;
		}

	} else {
		printFrnEUSearchException(jQuery(xml).find("message").text()) ;
	}

}

function setFrnEUResult(xml) {

	if (jQuery(xml).find("flag").text() == "SUCCESS") {

		setFrnEUResultCountBoard("<em class=\"txt_bold\">" + numberFormat(jQuery(xml).find("search").find("searchFound").text()) + "</em>건 검색") ;

		var searchResultCount = parseInt(jQuery(xml).find("search").find("searchFound").text()) ;

		setFrnEUSearchResultCount(searchResultCount) ;

		setFrnEUResultList(xml) ;

	} else {

		frnEULoadingDisplay = false ;
		hideFrnEULoading() ;

		jQuery("#frnEUResultList").empty() ;
		jQuery("#frnEUResultMore").hide() ;

		setFrnEUSearchResultCount(-1) ;
		printFrnEUSearchException(jQuery(xml).find("message").text()) ;

	}

}

function printFrnEUSearchException(V) {

	var newTagStr = "<li>" ;
	newTagStr += "<div class=\"search_section_title\">" ;
	newTagStr += "<h3>" + V + "</h3>" ;
	newTagStr += "</div>" ;
	newTagStr += "</li>" ;

	setFrnEUResultCountBoard(null) ;

	jQuery("#frnEUResultList").empty() ;
	jQuery("#frnEUResultMore").hide() ;

	$("#frnEUResultList").append(newTagStr) ;

}

var frnEUFadeTimerId = null ;
var frnEUFadeValue = 0 ;
var frnEULoadingDisplay = true ;
function showFrnEULoading() {
	if (frnEULoadingDisplay) {

		if (isPageError) {
			if (frnEUFadeTimerId) {
				window.clearInterval(frnEUFadeTimerId) ;
				frnEUFadeTimerId = null ;
				frnEUFadeValue = 0 ;
			}
			jQuery("#frnEUResultLoadingBoard").width(jQuery("#frnEUResultList").width()).height(jQuery("#frnEUResultList").height()) ;
			jQuery("#frnEUResultLoadingBoard").css(
							{
								"margin-top" : jQuery("#frnEUTitle").outerHeight(true)
							}
					) ;

			jQuery("#frnEUResultLoading").css(
							{
								"margin-top": ((jQuery("#frnEUResultList").height() / 2) - (jQuery("#frnEUResultLoading").height() / 2)) + jQuery("#frnEUTitle").outerHeight(true)
								, "margin-left": parseInt((jQuery("#frnEUResultList").width() / 2) - (jQuery("#frnEUResultLoading").width() / 2))
							}
					) ;
			jQuery("#frnEUResultLoading").show() ;
		} else {

			if (frnEUFadeTimerId == void 0) {
				frnEUFadeTimerId = window.setInterval(showFrnEULoading, 10) ;
				jQuery("#frnEUResultLoadingBoard").width(jQuery("#frnEUResultList").width()).height(jQuery("#frnEUResultList").height()) ;
				jQuery("#frnEUResultLoadingBoard").css(
								{
									"margin-top" : jQuery("#frnEUTitle").outerHeight(true)
								}
						) ;

				jQuery("#frnEUResultLoading").css(
								{
									"margin-top": ((jQuery("#frnEUResultList").height() / 2) - (jQuery("#frnEUResultLoading").height() / 2)) + jQuery("#frnEUTitle").outerHeight(true)
									, "margin-left": parseInt((jQuery("#frnEUResultList").width() / 2) - (jQuery("#frnEUResultLoading").width() / 2))
								}
						) ;

			}
			jQuery("#frnEUResultLoadingBoard").fadeTo(0, frnEUFadeValue * 0.08) ;
			if (frnEUFadeValue >= 10) {
				window.clearInterval(frnEUFadeTimerId) ;
				frnEUFadeTimerId = null ;
				jQuery("#frnEUResultLoading").show() ;
				frnEUFadeValue = 0 ;
			} else {
				frnEUFadeValue++ ;
			}
		}
	} else {
		if (frnEUFadeTimerId) {
			window.clearInterval(frnEUFadeTimerId) ;
			frnEUFadeTimerId = null ;
			frnEUFadeValue = 0 ;
		}
		hideFrnEULoading() ;
	}
}

function hideFrnEULoading() {
	jQuery("#frnEUResultLoading").fadeOut(1000) ;
	jQuery("#frnEUResultLoadingBoard").fadeOut(1000) ;
	jQuery("#frnEUResultLoadingBoard").width(0).height(0) ;
	jQuery("#frnEUResultLoading").hide() ;
	jQuery("#frnEUResultLoadingBoard").hide() ;
}

function getFrnEUSearchResult(keyword, expression) {

	frnEUResultXmlData = null ;

	jQuery("#resultFrnEU").show() ;
	frnEULoadingDisplay = true ;
	showFrnEULoading() ;

	setFrnEUResultCountBoard("검색 중입니다.") ;

	setFrnEUSearchResultCount(-1) ;

	jQuery.ajax({
		type : "POST" ,
		dataType : "xml" ,
		url : "/kportal/resulta.do" ,
		data : {
				next : "frnEUList"
				, FROM : "SEARCH"
				, searchInTransKorToEng : ((isSearchExtends) ? "Y" : "N")
				, searchInTransEngToKor : ((isSearchExtends) ? "Y" : "N")
				, row : "3"
				, queryText : keyword
				, expression : expression
		} ,
		success : function(xml, textStatus) {
			frnEUResultXmlData = xml ;
			setFrnEUResult(xml) ;
		} ,
		error : function(xhr, textStatus) {
			frnEULoadingDisplay = false ;
			hideFrnEULoading() ;
			printFrnEUSearchException("검색 도중 오류가 발생하였습니다.[" + xhr.status + "]") ;
		}
	}) ;
}


</script>





<form name="frnJPMoreFrm" id="frnJPMoreFrm" method="post">
				<section id="resultFrnJP" class="search_section">
					<div id="frnJPResultLoadingBoard"></div>
					<div id="frnJPResultLoading"><img src="/kportal/images/common/loading_foreign.gif" alt="해외특허 검색결과를 불러오고 있습니다." /></div>
					<h2 id="frnJPTitle" class="total_title">[일본] <button type="submit" id="moreFrnJPResult2" ><span id="frnJPResultCountBoard"><em class="txt_bold"></em>건 검색</span></button></h2>
					<div id="frnJPResultList">
						<div class="search_blank"></div>
					</div>
                                        <input type="hidden" name="next" value="frnJP" />
                                        <input type="hidden" id="frnJPQueryText" name="queryText" value="" />
                                        <input type="hidden" id="frnJPExpression" name="expression" value="" />
                                        <input type="hidden" id="frnJPSearchInTrans" name="searchInTrans" value="" />
                                        <input type="hidden" name="config" value="G1111111111111111111111S110001000000000000" />
                                        <input type="hidden" name="numPerPage" value="30" />
                                        <input type="hidden" name="currentPage" value="1" />
                                        <input type="hidden" name="sortField1" value="Score" />
                                        <input type="hidden" name="sortState1" value="Desc" />
                                        <input type="hidden" name="nowTab" value="PAJ_T.col" />
                                        <input type="hidden" name="collectionValues" value="PAJ_T.col" />
					<p id="frnJPResultMore" class="total_more">
						<span class="more_plus"><button type="submit" id="goFrnJPResult" >해외특허(일본)<span style="color:#00a13a"> 더보기</span></button></span>
						<span class="more"><button type="submit" id="moreFrnJPResult" >통합검색<span style="color:#00a13a"> 더보기</span></button></span>
					</p>
                                </section>
</form>
				
<script type="text/javascript">

jQuery("#moreFrnJPResult").click(
	function(evt) {
		jQuery("#frnJPMoreFrm").prop("action", "/kportal/search/search_frn_jp.do") ;
	}
) ;
jQuery("#moreFrnJPResult2").click(
	function(evt) {
		jQuery("#frnJPMoreFrm").prop("action", "/kportal/search/search_frn_jp.do") ;
	}
) ;
jQuery("#goFrnJPResult").click(
	function(evt) {
		jQuery("#frnJPMoreFrm").prop("action", "https://www.kipris.or.kr/abpat/searchLogina.do?next=MainSearch") ;
	}
) ;

var frnJPResultXmlData = null ;

function addFrnJPResult(xml) {

	var articleIdx = 0 ;
	jQuery(xml).find("search").find("articles").find("article").each(
		function(idx) {

			var newTagStr = "" ;

			if (resultViewMode == "TEXT") {

				newTagStr += '<article>' ;
				newTagStr += '	<div class="search_section_title">' ;
				//newTagStr += '		<span class="float_left"><input type="checkbox" id="search_extend" /></span>' ;
				newTagStr += '		<h1 class="stitle"><span class="icon_flag"><img src="/kportal/images/flag/icon_pj.gif" alt="JP(일본)" /></span><a href="{VIEW_LINK}" title="새창으로 열림"> {TL} </a></h1>' ; 
				newTagStr += '		<div class="btn_doc">' ;

                                if (jQuery(this).find("examinedTextFg").text() == "Y") {
                                        newTagStr += '	<a href="{LINK_FULL_TEXT}" title="공보 새창으로 열림"><img src="/kportal/images/button/btn_kor.gif" alt="공보" /></a>' ;
                                }
                                newTagStr += '	        </div>' ;
				newTagStr += '	</div>' ;
				newTagStr += '	<div class="search_basic_info">' ;
				newTagStr += '		<ul class="noimg_list">' ;
				newTagStr += '			<li class="left_width"><span>IPC :</span> <span class="point01">{IPC}</span></li>' ;
				newTagStr += '			<li class="right_width"><span>CPC :</span> <span class="point01">{CPC}</span></li>' ;
				newTagStr += '			<li class="left_width"><span>출원번호 :</span> <a href="{VIEW_LINK}" title="새창으로 열림">{AN}</a></li>' ;
				newTagStr += '			<li class="right_width"><span>출원일자 :</span> {AD}</li>' ;
				newTagStr += '			<li class="left_width"><span>등록번호 :</span> {GN}</li>' ;
				newTagStr += '			<li class="right_width"><span>등록일자 :</span> {GD}</li>' ;
				newTagStr += '			<li class="left_width"><span>공개번호 :</span> {OPN}</li>' ;
				newTagStr += '			<li class="right_width"><span>공개일자 :</span> {OPD}</li>' ;
				newTagStr += '			<li class="left_width"><span>공보번호 :</span> {PN}</li>' ;
				newTagStr += '			<li class="right_width"><span>공보일자 :</span> {PD}</li>' ;
                                newTagStr += '			<li class="left_width"><span>출원인 :</span> <font title="{AP}">{AP}</font></li>' ;
				newTagStr += '		</ul>' ;
				newTagStr += '		<div class="search_detail_content">' ;
				newTagStr += '			<div class="search_txt">' ;
				newTagStr += '				<span class="btn_abstract"><img src="/kportal/images/button/btn_abstract.gif" alt="요약" /></span>' ;
				newTagStr += '				{AB}' ;
				newTagStr += '			</div>' ;
				newTagStr += '		</div>' ;
				newTagStr += '	</div>' ;
				newTagStr += '</article>' ;

			} else {

				newTagStr += '<article>' ;
				newTagStr += '	<div class="search_section_title">' ;
				newTagStr += '		<h1 class="stitle"><span class="icon_flag"><img src="/kportal/images/flag/icon_pj.gif" alt="JP(일본)" /></span><a href="{VIEW_LINK}" title="새창으로 열림"> {TL} </a></h1>' ; 
				newTagStr += '		<div class="btn_doc">' ;

                                if (jQuery(this).find("examinedTextFg").text() == "Y") {
                                        newTagStr += '	<a href="{LINK_FULL_TEXT}" title="공보 새창으로 열림"><img src="/kportal/images/button/btn_kor.gif" alt="공보" /></a>' ;
                                }
                                
                                newTagStr += '	        </div>' ;
				newTagStr += '	</div>' ;
				newTagStr += '	<div class="search_basic_info">' ;
				//newTagStr += '		<ul class="search_info_list">' ;
                                newTagStr += '		<div class="thumb"><a href="{VIEW_IMAGE_LINK}" title="새창으로 열림"><img src="{IMG_SRC}" width="100" height="100" alt="{IMG_ALT}" /></a></div>' ;
                                newTagStr += '		<ul class="search_info_list">' ;
				newTagStr += '			<li class="left_width"><span>IPC :</span> <span class="point01">{IPC}</span></li>' ;
				newTagStr += '			<li class="right_width"><span>CPC :</span> <span class="point01">{CPC}</span></li>' ;
				newTagStr += '			<li class="left_width"><span>출원번호 :</span> <a href="{VIEW_LINK}" title="새창으로 열림">{AN}</a></li>' ;
				newTagStr += '			<li class="right_width"><span>출원일자 :</span> {AD}</li>' ;
				newTagStr += '			<li class="left_width"><span>등록번호 :</span> {GN}</li>' ;
				newTagStr += '			<li class="right_width"><span>등록일자 :</span> {GD}</li>' ;
				newTagStr += '			<li class="left_width"><span>공개번호 :</span> {OPN}</li>' ;
				newTagStr += '			<li class="right_width"><span>공개일자 :</span> {OPD}</li>' ;
				newTagStr += '			<li class="left_width"><span>공보번호 :</span> {PN}</li>' ;
				newTagStr += '			<li class="right_width"><span>공보일자 :</span> {PD}</li>' ;
                                newTagStr += '			<li class="left_width"><span>출원인 :</span> <font title="{AP}">{AP}</font></li>' ;
				newTagStr += '		</ul>' ;
				newTagStr += '	</div>' ;
				newTagStr += '</article>' ;

			}

			var AB = jQuery(this).find("AB").text() ;
			if (AB == "내용 없음" || AB == "내용없음" || AB == "내용 없음.") { AB = "" ; }
			if (AB == "") {
				AB = '<span class="no_abstract">내용 없음</span>' ;
			}

			newTagStr = newTagStr.replace(/{VIEW_LINK}/g, "javascript:viewForeignPatent('{VdkVgwKey}', '{COLLECTION}', '{PAGE}', '{COUNTRY}', '{ARTICLE_IDX}')") ;
			newTagStr = newTagStr.replace(/{LINK_FULL_TEXT}/g, "javascript:openDetailAbpat('{VdkVgwKey}', '{COLLECTION}', '{PAGE}', '{COUNTRY}', '{ARTICLE_IDX}')") ;

			newTagStr = newTagStr.replace(/{VdkVgwKey}/g, jQuery(this).find("VdkVgwKey").text()) ;
			newTagStr = newTagStr.replace(/{COLLECTION}/g, "PAJ_T.col") ;
			newTagStr = newTagStr.replace(/{PAGE}/g, jQuery(xml).find("search").find("page").find("searchPage").text()) ;
			newTagStr = newTagStr.replace(/{COUNTRY}/g, jQuery(this).find("CC").text()) ;
			newTagStr = newTagStr.replace(/{ARTICLE_IDX}/g, articleIdx) ;
			newTagStr = newTagStr.replace(/{TL}/g, jQuery(this).find("TL").text()) ;
			newTagStr = newTagStr.replace(/{IPC}/g, jQuery(this).find("IPC").text()) ;
                        newTagStr = newTagStr.replace(/{CPC}/g, jQuery(this).find("CPC").text()) ;
			newTagStr = newTagStr.replace(/{AP}/g, jQuery(this).find("AP").text()) ;
			newTagStr = newTagStr.replace(/{AN}/g, jQuery(this).find("AN").text()) ;
			newTagStr = newTagStr.replace(/{AD}/g, dateFormat(jQuery(this).find("AD").text(), "yyyy.mm.dd")) ;
			newTagStr = newTagStr.replace(/{GN}/g, jQuery(this).find("GN").text()) ;
			newTagStr = newTagStr.replace(/{GD}/g, dateFormat(jQuery(this).find("GD").text(), "yyyy.mm.dd")) ;
			newTagStr = newTagStr.replace(/{OPN}/g, jQuery(this).find("OPN").text()) ;
			newTagStr = newTagStr.replace(/{OPD}/g, dateFormat(jQuery(this).find("OPD").text(), "yyyy.mm.dd")) ;
			newTagStr = newTagStr.replace(/{PN}/g, jQuery(this).find("PN").text()) ;
			newTagStr = newTagStr.replace(/{PD}/g, dateFormat(jQuery(this).find("PD").text(), "yyyy.mm.dd")) ;
                        newTagStr = newTagStr.replace(/{IMG_SRC}/g, jQuery(this).find("IMG").find("src").text()) ;
                        newTagStr = newTagStr.replace(/{IMG_ALT}/g, jQuery(this).find("IMG").find("alt").text()) ;
                        newTagStr = newTagStr.replace(/{VIEW_IMAGE_LINK}/g, "javascript:OpenFrontDrawPopABPAT('"+jQuery(this).find("VdkVgwKey").text().replace(",","")+"','JP')");
		
			newTagStr = newTagStr.replace(/{AB}/g, AB) ;

			var newTag = jQuery(newTagStr) ;
			$("#frnJPResultList").append(newTag) ;

			articleIdx++ ;
		}
	) ;
}

function setFrnJPResultCountBoard(V) {
	if (V == void 0 || V == null) {
		jQuery("#frnJPResultCountBoard").empty() ;
	} else {
		jQuery("#frnJPResultCountBoard").html(V) ;
	}
}

function setFrnJPResultViewMode() {
	setFrnJPResultList(frnJPResultXmlData) ;
}

function changeFrnJPResultViewMode() {
	frnJPLoadingDisplay = true ;
	showFrnJPLoading() ;
	window.setTimeout(setFrnJPResultViewMode, 500) ;
}

function setFrnJPResultList(xml) {

	frnJPLoadingDisplay = false ;
	hideFrnJPLoading() ;

	jQuery("#frnJPResultList").empty() ;

	jQuery("#frnJPResultMore").hide() ;

	var searchResultCount = parseInt(jQuery(xml).find("search").find("searchFound").text()) ;

	if (searchResultCount > 0) {

		addFrnJPResult(xml) ;

		if (parseInt(jQuery(xml).find("search").find("searchFound").text()) > 0) {

			jQuery("#frnJPQueryText").val(jQuery(xml).find("search").find("searchKeyword").text()) ;
			jQuery("#frnJPExpression").val(jQuery(xml).find("search").find("searchExpression").text()) ;

			jQuery("#frnJPSearchInTrans").val(jQuery(xml).find("search").find("searchExtend").text()) ;

			jQuery("#frnJPResultMore").show() ;
		}

	} else {
		printFrnJPSearchException(jQuery(xml).find("message").text()) ;
	}

}

function setFrnJPResult(xml) {

	if (jQuery(xml).find("flag").text() == "SUCCESS") {

		setFrnJPResultCountBoard("<em class=\"txt_bold\">" + numberFormat(jQuery(xml).find("search").find("searchFound").text()) + "</em>건 검색") ;

		var searchResultCount = parseInt(jQuery(xml).find("search").find("searchFound").text()) ;

		setFrnJPSearchResultCount(searchResultCount) ;

		setFrnJPResultList(xml) ;

	} else {

		frnJPLoadingDisplay = false ;
		hideFrnJPLoading() ;

		jQuery("#frnJPResultList").empty() ;
		jQuery("#frnJPResultMore").hide() ;

		setFrnJPSearchResultCount(-1) ;
		printFrnJPSearchException(jQuery(xml).find("message").text()) ;

	}

}

function printFrnJPSearchException(V) {

	var newTagStr = "<li>" ;
	newTagStr += "<div class=\"search_section_title\">" ;
	newTagStr += "<h3>" + V + "</h3>" ;
	newTagStr += "</div>" ;
	newTagStr += "</li>" ;

	setFrnJPResultCountBoard(null) ;

	jQuery("#frnJPResultList").empty() ;
	jQuery("#frnJPResultMore").hide() ;

	$("#frnJPResultList").append(newTagStr) ;

}

var frnJPFadeTimerId = null ;
var frnJPFadeValue = 0 ;
var frnJPLoadingDisplay = true ;
function showFrnJPLoading() {
	if (frnJPLoadingDisplay) {

		if (isPageError) {
			if (frnJPFadeTimerId) {
				window.clearInterval(frnJPFadeTimerId) ;
				frnJPFadeTimerId = null ;
				frnJPFadeValue = 0 ;
			}
			jQuery("#frnJPResultLoadingBoard").width(jQuery("#frnJPResultList").width()).height(jQuery("#frnJPResultList").height()) ;
			jQuery("#frnJPResultLoadingBoard").css(
							{
								"margin-top" : jQuery("#frnJPTitle").outerHeight(true)
							}
					) ;

			jQuery("#frnJPResultLoading").css(
							{
								"margin-top": ((jQuery("#frnJPResultList").height() / 2) - (jQuery("#frnJPResultLoading").height() / 2)) + jQuery("#frnJPTitle").outerHeight(true)
								, "margin-left": parseInt((jQuery("#frnJPResultList").width() / 2) - (jQuery("#frnJPResultLoading").width() / 2))
							}
					) ;
			jQuery("#frnJPResultLoading").show() ;
		} else {

			if (frnJPFadeTimerId == void 0) {
				frnJPFadeTimerId = window.setInterval(showFrnJPLoading, 10) ;
				jQuery("#frnJPResultLoadingBoard").width(jQuery("#frnJPResultList").width()).height(jQuery("#frnJPResultList").height()) ;
				jQuery("#frnJPResultLoadingBoard").css(
								{
									"margin-top" : jQuery("#frnJPTitle").outerHeight(true)
								}
						) ;

				jQuery("#frnJPResultLoading").css(
								{
									"margin-top": ((jQuery("#frnJPResultList").height() / 2) - (jQuery("#frnJPResultLoading").height() / 2)) + jQuery("#frnJPTitle").outerHeight(true)
									, "margin-left": parseInt((jQuery("#frnJPResultList").width() / 2) - (jQuery("#frnJPResultLoading").width() / 2))
								}
						) ;

			}
			jQuery("#frnJPResultLoadingBoard").fadeTo(0, frnJPFadeValue * 0.08) ;
			if (frnJPFadeValue >= 10) {
				window.clearInterval(frnJPFadeTimerId) ;
				frnJPFadeTimerId = null ;
				jQuery("#frnJPResultLoading").show() ;
				frnJPFadeValue = 0 ;
			} else {
				frnJPFadeValue++ ;
			}
		}
	} else {
		if (frnJPFadeTimerId) {
			window.clearInterval(frnJPFadeTimerId) ;
			frnJPFadeTimerId = null ;
			frnJPFadeValue = 0 ;
		}
		hideFrnJPLoading() ;
	}
}

function hideFrnJPLoading() {
	jQuery("#frnJPResultLoading").fadeOut(1000) ;
	jQuery("#frnJPResultLoadingBoard").fadeOut(1000) ;
	jQuery("#frnJPResultLoadingBoard").width(0).height(0) ;
	jQuery("#frnJPResultLoading").hide() ;
	jQuery("#frnJPResultLoadingBoard").hide() ;
}

function getFrnJPSearchResult(keyword, expression) {

	frnJPResultXmlData = null ;

	jQuery("#resultFrnJP").show() ;
	frnJPLoadingDisplay = true ;
	showFrnJPLoading() ;

	setFrnJPResultCountBoard("검색 중입니다.") ;

	setFrnJPSearchResultCount(-1) ;

	jQuery.ajax({
		type : "POST" ,
		dataType : "xml" ,
		url : "/kportal/resulta.do" ,
		data : {
				next : "frnJPList"
				, FROM : "SEARCH"
				, searchInTransKorToEng : ((isSearchExtends) ? "Y" : "N")
				, searchInTransEngToKor : ((isSearchExtends) ? "Y" : "N")
				, row : "3"
				, queryText : keyword
				, expression : expression
		} ,
		success : function(xml, textStatus) {
			frnJPResultXmlData = xml ;
			setFrnJPResult(xml) ;
		} ,
		error : function(xhr, textStatus) {
			frnJPLoadingDisplay = false ;
			hideFrnJPLoading() ;
			printFrnJPSearchException("검색 도중 오류가 발생하였습니다.[" + xhr.status + "]") ;
		}
	}) ;
}


</script>





















	<form name="ipnaviPrcdnMoreFrm" id="ipnaviPrcdnMoreFrm" method="post">
	<section id="resultIpnaviPrcdn" class="search_section">
		<div id="ipnaviPrcdnResultLoadingBoard"></div>
		<div id="ipnaviPrcdnResultLoading"><img src="/kportal/images/common/loading_ipnavi.gif" alt="IPNAVI 검색결과를 불러오고 있습니다." /></div>
		<h2 id="ipnaviPrcdnTitle" class="total_title">[IPNAVI-판례정보] <span id="ipnaviPrcdnResultCountBoard"><em class="txt_bold">-</em>건 검색</span></h2>
		<div id="ipnaviPrcdnResultList">
			<div class="search_blank"></div>
		</div>
			<input type="hidden" id="next" name="next" value="listPrcdn" />
			<input type="hidden" id="ipnaviPrcdnQueryText" name="queryText" value="" />
			<input type="hidden" id="ipnaviPrcdnQuery" name="query" value="" />
			<input type="hidden" id="ipnaviPrcdnExpression" name="expression" value="" />
			<input type="hidden" id="ipnaviMaxCount" name="maxCount" value="10"/>
			<input type="hidden" id="ipnaviPageNum" name="pageNum" value="1"/>
			<input type="hidden" id="ipnaviCategory" name="category" value="prcdn"/>
			<input type="hidden" id="ipnaviSearchInTrans" name="searchInTrans" value="" />
			<p id="ipnaviPrcdnResultMore" class="total_more">
				<span class="more"><button type="submit" id="moreIpnaviPrcdnResult" >통합검색 <span style="color:#00a13a">더보기</span></button></span>
				<!--  
				<span class="more_plus"><button type="submit" id="goIpnaviPrcdnResult" >IPNAVI(판례)<font style="color:#00a13a">더보기</font></button></span>
				-->
			</p>
	</section>
	</form>

<script type="text/javascript">

jQuery("#moreIpnaviPrcdnResult").click(
	function(evt) {
		jQuery("#ipnaviPrcdnMoreFrm").prop("action", "/kportal/search/search_ipnavi_prcdn.do") ;
	}
) ;
jQuery("#goIpnaviPrcdnResult").click(
	function(evt) {
		jQuery("#ipnaviPrcdnMoreFrm").prop("action", "https://www.kipris.or.kr/kpat/resulta.do?next=ResultList") ;
	}
) ;

var ipnaviPrcdnResultXmlData = null ;

function addIpnaviPrcdnResult(xml) {

	var articleIdx = 0 ;

	jQuery(xml).find("search").find("articles").find("article").each(

		function(idx) {
			var newTagStr = "" ;

			newTagStr += '<article>' ;
			newTagStr += '    <div class="search_section_title">' ;
			newTagStr += '        <h1 class="stitle">' ;
			newTagStr += '            <a href="https://www.ip-navi.or.kr/ipnavi/precedent/biblioPopup.navi?scaseId={scaseId}" onclick="window.open(this.getAttribute(\'href\'),\'ipnavi\',\'scrollbars=yes, resizable=yes\'); return false;" target="_blank">{stitle}</a>' ;
			newTagStr += '        </h1>' ;
			newTagStr += '    </div>' ;
			newTagStr += '    <div class="search_basic_info">' ;
			newTagStr += '        <ul class="noimg_list">' ;
			newTagStr += '            <li class="left_width"><span>사건명 :</span> {stitle}</li>' ;
			newTagStr += '            <li class="right_width"><span>쟁점기술 :</span> {stechIssue}</li>' ;
			newTagStr += '            <li class="left_width"><span>사건번호 :</span> {scaseNoArr}</li>' ;
			newTagStr += '            <li class="right_width"><span>원고측 :</span> {sstorPltfArr}</li>' ;
			newTagStr += '            <li class="left_width"><span>피고측 :</span> {sstorDfdtArr}</li>' ;
			newTagStr += '            <li class="right_width"><span>법원명 :</span> {scrt}</li>' ;
			newTagStr += '            <li class="left_width"><span>판결일자 :</span> {sdcsnDt}</li>' ;
			newTagStr += '            <li class="right_width"><span>기술분야 :</span> {stechName}</li>' ;
			newTagStr += '            <li class="left_width"><span>관련 IPC :</span> {refIpc}</li>' ;
			newTagStr += '        </ul>' ;
			//newTagStr += '        <div class="search_detail_content">' ;
			//newTagStr += '            <div class="search_txt">' ;
			//newTagStr += '                <span class="btn_abstract"><img src="/kportal/images/button/btn_abstract.gif" alt="요약" /></span>{ssmryTitle}' ;
			//newTagStr += '            </div>' ;
			//newTagStr += '        </div>' ;
			newTagStr += '    </div>' ;
			newTagStr += '</article>' ;
			
			newTagStr = newTagStr.replace(/{scaseId}/g, jQuery(this).find("scaseId").text()) ;
			newTagStr = newTagStr.replace(/{stitle}/g, jQuery(this).find("stitle").text()) ;
			newTagStr = newTagStr.replace(/{stechIssue}/g, jQuery(this).find("stechIssue").text()) ;
			newTagStr = newTagStr.replace(/{scaseNoArr}/g, jQuery(this).find("scaseNoArr").text()) ;
			newTagStr = newTagStr.replace(/{sstorPltfArr}/g, jQuery(this).find("sstorPltfArr").text()) ;
			newTagStr = newTagStr.replace(/{sstorDfdtArr}/g, jQuery(this).find("sstorDfdtArr").text()) ;
			newTagStr = newTagStr.replace(/{scrt}/g, jQuery(this).find("scrt").text()) ;
			newTagStr = newTagStr.replace(/{sdcsnDt}/g, jQuery(this).find("sdcsnDt").text()) ;
			newTagStr = newTagStr.replace(/{stechName}/g, jQuery(this).find("stechName").text()) ;
			newTagStr = newTagStr.replace(/{refIpc}/g, jQuery(this).find("refIpc").text()) ;
			newTagStr = newTagStr.replace(/{ssmryTitle}/g, jQuery(this).find("ssmryTitle").text()) ;
			
			var newTag = jQuery(newTagStr) ;
			$("#ipnaviPrcdnResultList").append(newTag) ;

			articleIdx++ ;
		}
	) ;

}

function setIpnaviPrcdnResultCountBoard(V) {
	if (V == void 0 || V == null) {
		jQuery("#ipnaviPrcdnResultCountBoard").empty() ;
	} else {
		jQuery("#ipnaviPrcdnResultCountBoard").html(V) ;
	}
}

function setIpnaviPrcdnResultViewMode() {
	setIpnaviPrcdnResultList(ipnaviPrcdnResultXmlData) ;
}

function changeIpnaviPrcdnResultViewMode() {
	ipnaviPrcdnLoadingDisplay = true ;
	showIpnaviPrcdnLoading() ;
	window.setTimeout(setIpnaviPrcdnResultViewMode, 500) ;
}

function setIpnaviPrcdnResultList(xml) {

	ipnaviPrcdnLoadingDisplay = false ;
	hideIpnaviPrcdnLoading() ;

	jQuery("#ipnaviPrcdnResultList").empty() ;

	jQuery("#ipnaviPrcdnResultMore").hide() ;

	var searchResultCount = parseInt(jQuery(xml).find("search").find("searchFound").text()) ;

	if (searchResultCount > 0) {

		addIpnaviPrcdnResult(xml) ;

		if (parseInt(jQuery(xml).find("search").find("searchFound").text()) > 0) {

			jQuery("#ipnaviPrcdnQueryText").val(jQuery(xml).find("search").find("searchKeyword").text()) ;
			jQuery("#ipnaviPrcdnExpression").val(jQuery(xml).find("search").find("searchExpression").text()) ;

			jQuery("#ipnaviSearchInTrans").val(jQuery(xml).find("search").find("searchExtend").text()) ;

			jQuery("#ipnaviPrcdnResultMore").show() ;
			
		}

	} else {
		printIpnaviPrcdnSearchException(jQuery(xml).find("message").text()) ;
	}

}

function setIpnaviPrcdnResult(xml) {

	if (jQuery(xml).find("flag").text() == "SUCCESS") {

		setIpnaviPrcdnResultCountBoard("<em class=\"txt_bold\">" + numberFormat(jQuery(xml).find("search").find("searchFound").text()) + "</em>건 검색") ;

		var searchResultCount = parseInt(jQuery(xml).find("search").find("searchFound").text()) ;

		setIpNaviPrcdnSearchResultCount(searchResultCount) ;

		setIpnaviPrcdnResultList(xml) ;

	} else {

		ipnaviPrcdnLoadingDisplay = false ;
		hideIpnaviPrcdnLoading() ;

		jQuery("#ipnaviPrcdnResultList").empty() ;
		jQuery("#ipnaviPrcdnResultMore").hide() ;

		setIpNaviPrcdnSearchResultCount(-1) ;
		printIpnaviPrcdnSearchException(jQuery(xml).find("message").text()) ;

	}

}

function printIpnaviPrcdnSearchException(V) {

	var newTagStr = "<li>" ;
	newTagStr += "<div class=\"search_section_title\">" ;
	newTagStr += "<h3>" + V + "</h3>" ;
	newTagStr += "</div>" ;
	newTagStr += "</li>" ;

	setIpnaviPrcdnResultCountBoard(null) ;

	jQuery("#ipnaviPrcdnResultList").empty() ;
	jQuery("#ipnaviPrcdnResultMore").hide() ;

	$("#ipnaviPrcdnResultList").append(newTagStr) ;

}

var ipnaviPrcdnFadeTimerId = null ;
var ipnaviPrcdnFadeValue = 0 ;
var ipnaviPrcdnLoadingDisplay = true ;
function showIpnaviPrcdnLoading() {
	if (ipnaviPrcdnLoadingDisplay) {

		if (isPageError) {
			if (ipnaviPrcdnFadeTimerId) {
				window.clearInterval(ipnaviPrcdnFadeTimerId) ;
				ipnaviPrcdnFadeTimerId = null ;
				ipnaviPrcdnFadeValue = 0 ;
			}
			jQuery("#ipnaviPrcdnResultLoadingBoard").width(jQuery("#ipnaviPrcdnResultList").width()).height(jQuery("#ipnaviPrcdnResultList").height()) ;
			jQuery("#ipnaviPrcdnResultLoadingBoard").css(
							{
								"margin-top" : jQuery("#ipnaviPrcdnTitle").outerHeight(true)
							}
					) ;

			jQuery("#ipnaviPrcdnResultLoading").css(
							{
								"margin-top": ((jQuery("#ipnaviPrcdnResultList").height() / 2) - (jQuery("#ipnaviPrcdnResultLoading").height() / 2)) + jQuery("#ipnaviPrcdnTitle").outerHeight(true)
								, "margin-left": parseInt((jQuery("#ipnaviPrcdnResultList").width() / 2) - (jQuery("#ipnaviPrcdnResultLoading").width() / 2))
							}
					) ;
			jQuery("#ipnaviPrcdnResultLoading").show() ;
		} else {

			if (ipnaviPrcdnFadeTimerId == void 0) {
				ipnaviPrcdnFadeTimerId = window.setInterval(showIpnaviPrcdnLoading, 10) ;
				jQuery("#ipnaviPrcdnResultLoadingBoard").width(jQuery("#ipnaviPrcdnResultList").width()).height(jQuery("#ipnaviPrcdnResultList").height()) ;
				jQuery("#ipnaviPrcdnResultLoadingBoard").css(
								{
									"margin-top" : jQuery("#ipnaviPrcdnTitle").outerHeight(true)
								}
						) ;

				jQuery("#ipnaviPrcdnResultLoading").css(
								{
									"margin-top": ((jQuery("#ipnaviPrcdnResultList").height() / 2) - (jQuery("#ipnaviPrcdnResultLoading").height() / 2)) + jQuery("#ipnaviPrcdnTitle").outerHeight(true)
									, "margin-left": parseInt((jQuery("#ipnaviPrcdnResultList").width() / 2) - (jQuery("#ipnaviPrcdnResultLoading").width() / 2))
								}
						) ;

			}
			jQuery("#ipnaviPrcdnResultLoadingBoard").fadeTo(0, ipnaviPrcdnFadeValue * 0.08) ;
			if (ipnaviPrcdnFadeValue >= 10) {
				window.clearInterval(ipnaviPrcdnFadeTimerId) ;
				ipnaviPrcdnFadeTimerId = null ;
				jQuery("#ipnaviPrcdnResultLoading").show() ;
				ipnaviPrcdnFadeValue = 0 ;
			} else {
				ipnaviPrcdnFadeValue++ ;
			}
		}
	} else {
		if (ipnaviPrcdnFadeTimerId) {
			window.clearInterval(ipnaviPrcdnFadeTimerId) ;
			ipnaviPrcdnFadeTimerId = null ;
			ipnaviPrcdnFadeValue = 0 ;
		}
		hideIpnaviPrcdnLoading() ;
	}
}

function hideIpnaviPrcdnLoading() {
	jQuery("#ipnaviPrcdnResultLoading").fadeOut(1000) ;
	jQuery("#ipnaviPrcdnResultLoadingBoard").fadeOut(1000) ;
	jQuery("#ipnaviPrcdnResultLoadingBoard").width(0).height(0) ;
	jQuery("#ipnaviPrcdnResultLoading").hide() ;
	jQuery("#ipnaviPrcdnResultLoadingBoard").hide() ;
}


function getIpNaviPrcdnSearchResult(keyword, expression) {

	
	ipnaviPrcdnResultXmlData = null ;

	jQuery("#resultIpnaviPrcdn").show() ;
	ipnaviPrcdnLoadingDisplay = true ;
	
	showIpnaviPrcdnLoading() ;
	
	setIpnaviPrcdnResultCountBoard("검색 중입니다.") ;

	setIpNaviPrcdnSearchResultCount(-1) ;

	
	jQuery.ajax({
		type : "POST" ,
		dataType : "xml" ,
		url : "/kportal/search/search_ipnavi.do" ,
		data : {
				next : "resultListPrcdn"
				, FROM : "SEARCH"
				, searchInTransKorToEng : ((isSearchExtends) ? "Y" : "N")
				, searchInTransEngToKor : ((isSearchExtends) ? "Y" : "N")
				, category: 'prcdn'
                                , pageNum : 1
                                , maxCount : jQuery("#searchResultSearchPageNum").val()
				//, maxCount : 3
				, query : keyword
				, queryText : keyword
				, expression : expression
		} ,
		success : function(xml, textStatus) {
			ipnaviPrcdnResultXmlData = xml ;
			setIpnaviPrcdnResult(xml) ;
		} ,
		error : function(xhr, textStatus) {
			ipnaviPrcdnLoadingDisplay = false ;
			hideIpnaviPrcdnLoading() ;
			printIpnaviPrcdnSearchException("검색 도중 오류가 발생하였습니다.[" + xhr.status + "]") ;
		}
	}) ;
}


</script>





	<section id="resultIpnaviConflict" class="search_section">
		<div id="ipnaviConflictResultLoadingBoard"></div>
		<div id="ipnaviConflictResultLoading"><img src="/kportal/images/common/loading_ipnavi.gif" alt="IPNAVI 검색결과를 불러오고 있습니다." /></div>
		<h2 id="ipnaviConflictTitle" class="total_title">[IPNAVI-분쟁정보] <span id="ipnaviConflictResultCountBoard"><em class="txt_bold">-</em>건 검색</span></h2>
		<div id="ipnaviConflictResultList">
			<div class="search_blank"></div>
		</div>
		<form name="ipnaviConflictMoreFrm" id="ipnaviConflictMoreFrm" method="post">
			<input type="hidden" id="next" name="next" value="listConflict" />
			<input type="hidden" id="ipnaviConflictQueryText" name="queryText" value="" />
			<input type="hidden" id="ipnaviConflictQuery" name="query" value="" />
			<input type="hidden" id="ipnaviConflictExpression" name="expression" value="" />
			<input type="hidden" id="ipnaviMaxCount1" name="maxCount" value="10"/>
			<input type="hidden" id="ipnaviPageNum1" name="pageNum" value="1"/>
			<input type="hidden" id="ipnaviCategory1" name="category" value="conflict"/>
			<input type="hidden" id="ipnaviConflictSearchInTrans" name="searchInTrans" value="" />
			<p id="ipnaviConflictResultMore" class="total_more">
				<span class="more"><button type="submit" id="moreIpnaviConflictResult" >통합검색 <span style="color:#00a13a">더보기</span></button></span>
				<!--  
				<span class="more_plus"><button type="submit" id="goIpnaviConflictResult" >IPNAVI(판례)<font style="color:#00a13a">더보기</font></button></span>
				-->
			</p>
		</form>
	</section>

<script type="text/javascript">


jQuery("#moreIpnaviConflictResult").click(
	function(evt) {
		jQuery("#ipnaviConflictMoreFrm").prop("action", "/kportal/search/search_ipnavi_conflict.do") ;
		//jQuery("#searchResultFrm").prop("action", "/kportal/search/search_ipnavi.do?category=conflict&next=listConflict") ;
		//$('#next').val('listConflict');
		//jQuery("#searchResultFrm").submit() ;
	}
) ;
jQuery("#goIpnaviConflictResult").click(
	function(evt) {
		jQuery("#ipnaviConflictMoreFrm").prop("action", "https://www.kipris.or.kr/kpat/resulta.do?next=ResultList") ;
	}
) ;

var ipnaviConflictResultXmlData = null ;

function addIpnaviConflictResult(xml) {

	var articleIdx = 0 ;

	jQuery(xml).find("search").find("articles").find("article").each(

		function(idx) {
			var newTagStr = "" ;

			newTagStr += '<article>' ;
			newTagStr += '    <div class="search_section_title">' ;
			newTagStr += '        <h1 class="stitle">' ;
			newTagStr += '            <a href="{disputeUrl}" onclick="window.open(this.getAttribute(\'href\'),\'ipnavi\',\'scrollbars=yes, resizable=yes\'); return false;" target="_blank">{title}</a>' ;
			newTagStr += '        </h1>' ;
			newTagStr += '    </div>' ;
			newTagStr += '    <div class="search_basic_info">' ;
			newTagStr += '        <ul class="noimg_list">' ;
			newTagStr += '            <li class="left_width"><span>사건번호 :</span> {acciNum}</li>' ;
			newTagStr += '            <li class="right_width"><span>원고명 :</span> {plaintiffName}</li>' ;
			newTagStr += '            <li class="left_width"><span>피고명 :</span> {defendantName}</li>' ;
			newTagStr += '            <li class="right_width"><span>발생일자 :</span> {acciDate}</li>' ;
			newTagStr += '            <li class="left_width"><span>침해권리 :</span> {rightsType}</li>' ;
			newTagStr += '            <li class="right_width"><span>법원국가 :</span> {courtCountry}</li>' ;
			newTagStr += '            <li class="left_width"><span>계쟁제품 :</span> {issueProduct}</li>' ;
			newTagStr += '        </ul>' ;			
			newTagStr += '    </div>' ;
			newTagStr += '</article>' ;
			
			newTagStr = newTagStr.replace(/{issueSeq}/g, jQuery(this).find("issueSeq").text()) ;
			newTagStr = newTagStr.replace(/{title}/g, jQuery(this).find("title").text()) ;
			
			newTagStr = newTagStr.replace(/{disputeUrl}/g, jQuery(this).find("disputeUrl").text()) ;
			
			newTagStr = newTagStr.replace(/{acciNum}/g, jQuery(this).find("acciNum").text()) ;
			newTagStr = newTagStr.replace(/{plaintiffName}/g, jQuery(this).find("plaintiffName").text()) ;			
			newTagStr = newTagStr.replace(/{defendantName}/g, jQuery(this).find("defendantName").text()) ;
			newTagStr = newTagStr.replace(/{acciDate}/g, jQuery(this).find("acciDate").text()) ;
			newTagStr = newTagStr.replace(/{rightsType}/g, jQuery(this).find("rightsType").text()) ;
			newTagStr = newTagStr.replace(/{courtCountry}/g, jQuery(this).find("courtCountry").text()) ;
			newTagStr = newTagStr.replace(/{issueProduct}/g, jQuery(this).find("issueProduct").text()) ;
			
			var newTag = jQuery(newTagStr) ;
			$("#ipnaviConflictResultList").append(newTag) ;

			articleIdx++ ;
		}
	) ;

}

function setIpnaviConflictResultCountBoard(V) {
	if (V == void 0 || V == null) {
		jQuery("#ipnaviConflictResultCountBoard").empty() ;
	} else {
		jQuery("#ipnaviConflictResultCountBoard").html(V) ;
	}
}

function setIpnaviConflictResultViewMode() {
	setIpnaviConflictResultList(ipnaviConflictResultXmlData) ;
}

function changeIpnaviConflictResultViewMode() {
	ipnaviConflictLoadingDisplay = true ;
	showIpnaviConflictLoading() ;
	window.setTimeout(setIpnaviConflictResultViewMode, 500) ;
}

function setIpnaviConflictResultList(xml) {

	ipnaviConflictLoadingDisplay = false ;
	hideIpnaviConflictLoading() ;

	jQuery("#ipnaviConflictResultList").empty() ;

	jQuery("#ipnaviConflictResultMore").hide() ;

	var searchResultCount = parseInt(jQuery(xml).find("search").find("searchFound").text()) ;

	if (searchResultCount > 0) {

		addIpnaviConflictResult(xml) ;

		if (parseInt(jQuery(xml).find("search").find("searchFound").text()) > 0) {

			jQuery("#ipnaviConflictQueryText").val(jQuery(xml).find("search").find("searchKeyword").text()) ;
			jQuery("#ipnaviConflictExpression").val(jQuery(xml).find("search").find("searchExpression").text()) ;

			jQuery("#ipnaviConflictSearchInTrans").val(jQuery(xml).find("search").find("searchExtend").text()) ;

			jQuery("#ipnaviConflictResultMore").show() ;
		}

	} else {
		printIpnaviConflictSearchException(jQuery(xml).find("message").text()) ;
	}

}

function setIpnaviConflictResult(xml) {

	if (jQuery(xml).find("flag").text() == "SUCCESS") {

		setIpnaviConflictResultCountBoard("<em class=\"txt_bold\">" + numberFormat(jQuery(xml).find("search").find("searchFound").text()) + "</em>건 검색") ;

		var searchResultCount = parseInt(jQuery(xml).find("search").find("searchFound").text()) ;

		setIpNaviConflictSearchResultCount(searchResultCount) ;

		setIpnaviConflictResultList(xml) ;

	} else {

		ipnaviConflictLoadingDisplay = false ;
		hideIpnaviConflictLoading() ;

		jQuery("#ipnaviConflictResultList").empty() ;
		jQuery("#ipnaviConflictResultMore").hide() ;

		setIpNaviConflictSearchResultCount(-1) ;
		printIpnaviConflictSearchException(jQuery(xml).find("message").text()) ;

	}

}

function printIpnaviConflictSearchException(V) {

	var newTagStr = "<li>" ;
	newTagStr += "<div class=\"search_section_title\">" ;
	newTagStr += "<h3>" + V + "</h3>" ;
	newTagStr += "</div>" ;
	newTagStr += "</li>" ;

	setIpnaviConflictResultCountBoard(null) ;

	jQuery("#ipnaviConflictResultList").empty() ;
	jQuery("#ipnaviConflictResultMore").hide() ;

	$("#ipnaviConflictResultList").append(newTagStr) ;

}

var ipnaviConflictFadeTimerId = null ;
var ipnaviConflictFadeValue = 0 ;
var ipnaviConflictLoadingDisplay = true ;
function showIpnaviConflictLoading() {
	if (ipnaviConflictLoadingDisplay) {

		if (isPageError) {
			if (ipnaviConflictFadeTimerId) {
				window.clearInterval(ipnaviConflictFadeTimerId) ;
				ipnaviConflictFadeTimerId = null ;
				ipnaviConflictFadeValue = 0 ;
			}
			jQuery("#ipnaviConflictResultLoadingBoard").width(jQuery("#ipnaviConflictResultList").width()).height(jQuery("#ipnaviConflictResultList").height()) ;
			jQuery("#ipnaviConflictResultLoadingBoard").css(
							{
								"margin-top" : jQuery("#ipnaviConflictTitle").outerHeight(true)
							}
					) ;

			jQuery("#ipnaviConflictResultLoading").css(
							{
								"margin-top": ((jQuery("#ipnaviConflictResultList").height() / 2) - (jQuery("#ipnaviConflictResultLoading").height() / 2)) + jQuery("#ipnaviConflictTitle").outerHeight(true)
								, "margin-left": parseInt((jQuery("#ipnaviConflictResultList").width() / 2) - (jQuery("#ipnaviConflictResultLoading").width() / 2))
							}
					) ;
			jQuery("#ipnaviConflictResultLoading").show() ;
		} else {

			if (ipnaviConflictFadeTimerId == void 0) {
				ipnaviConflictFadeTimerId = window.setInterval(showIpnaviConflictLoading, 10) ;
				jQuery("#ipnaviConflictResultLoadingBoard").width(jQuery("#ipnaviConflictResultList").width()).height(jQuery("#ipnaviConflictResultList").height()) ;
				jQuery("#ipnaviConflictResultLoadingBoard").css(
								{
									"margin-top" : jQuery("#ipnaviConflictTitle").outerHeight(true)
								}
						) ;

				jQuery("#ipnaviConflictResultLoading").css(
								{
									"margin-top": ((jQuery("#ipnaviConflictResultList").height() / 2) - (jQuery("#ipnaviConflictResultLoading").height() / 2)) + jQuery("#ipnaviConflictTitle").outerHeight(true)
									, "margin-left": parseInt((jQuery("#ipnaviConflictResultList").width() / 2) - (jQuery("#ipnaviConflictResultLoading").width() / 2))
								}
						) ;

			}
			jQuery("#ipnaviConflictResultLoadingBoard").fadeTo(0, ipnaviConflictFadeValue * 0.08) ;
			if (ipnaviConflictFadeValue >= 10) {
				window.clearInterval(ipnaviConflictFadeTimerId) ;
				ipnaviConflictFadeTimerId = null ;
				jQuery("#ipnaviConflictResultLoading").show() ;
				ipnaviConflictFadeValue = 0 ;
			} else {
				ipnaviConflictFadeValue++ ;
			}
		}
	} else {
		if (ipnaviConflictFadeTimerId) {
			window.clearInterval(ipnaviConflictFadeTimerId) ;
			ipnaviConflictFadeTimerId = null ;
			ipnaviConflictFadeValue = 0 ;
		}
		hideIpnaviConflictLoading() ;
	}
}

function hideIpnaviConflictLoading() {
	jQuery("#ipnaviConflictResultLoading").fadeOut(1000) ;
	jQuery("#ipnaviConflictResultLoadingBoard").fadeOut(1000) ;
	jQuery("#ipnaviConflictResultLoadingBoard").width(0).height(0) ;
	jQuery("#ipnaviConflictResultLoading").hide() ;
	jQuery("#ipnaviConflictResultLoadingBoard").hide() ;
}


function getIpNaviConflictSearchResult(keyword, expression) {

	ipnaviConflictResultXmlData = null ;

	jQuery("#resultIpnaviConflict").show() ;
	ipnaviConflictLoadingDisplay = true ;
	
	showIpnaviConflictLoading() ;
	setIpnaviConflictResultCountBoard("검색 중입니다.") ;

	setIpNaviConflictSearchResultCount(-1) ;

	jQuery.ajax({
		type : "POST" ,
		dataType : "xml" ,
		url : "/kportal/search/search_ipnavi.do" ,
		data : {
				next : "resultListConflict"
				, FROM : "SEARCH"
				, searchInTransKorToEng : ((isSearchExtends) ? "Y" : "N")
				, searchInTransEngToKor : ((isSearchExtends) ? "Y" : "N")
				, category: 'conflict'
				, maxCount : jQuery("#searchResultSearchPageNum").val()
                                , pageNum : 1
                                //, maxCount :3
				, query : keyword
				, queryText : keyword
				, expression : expression
		} ,
		success : function(xml, textStatus) {
			ipnaviConflictResultXmlData = xml ;
			setIpnaviConflictResult(xml) ;
		} ,
		error : function(xhr, textStatus) {
			ipnaviConflictLoadingDisplay = false ;
			hideIpnaviConflictLoading() ;
			printIpnaviConflictSearchException("검색 도중 오류가 발생하였습니다.[" + xhr.status + "]") ;
		}
	}) ;
}


</script>


<!-- TODO %@ include file="/search/result_ipnavi_guidebook.jspf" % -->


			</section>
                        <!-- 전체서비스 -->
                        <article class="all_service">
                                <h2><img src="/kportal/images/common/txt_allservice.gif" alt="전체서비스"/></h2>
                                <ul class="all_service_list">
                                        <li><a href="http://www.kipris.or.kr/khome/guideMaina.do">초보자검색</a></li>
                                        <li><a href="http://www.kipris.or.kr/khome/guide/easy/easy_potal.jsp">동영상메뉴얼</a></li>
                                        <li><a href="http://www.kipris.or.kr/khome/guide/customer/center.jsp">찾아가는 특허서비스</a></li>
                                        <li><a href="javascript:void(newPopupWindow('http://www.kipris.or.kr/khome/guide/easy/glossary/glossary02.jsp','GlossaryWin',700, 690, 'R', 'M', 'scrollbars=yes'));" title="용어사전 새창으로 열림">용어사전</a></li>
                                        <li><a href="http://www.kipris.or.kr/khome/help/help03/help03_1.jsp" onclick="newPopupWindow(this.href, 'help' ,820, 800, 'R', 'M', 'scrollbars=yes');return false;" target="_blank" title="검색도움말 새창으로 열림">검색도움말</a></li>
                                </ul>
                        </article>
			<!-- //전체서비스 -->
		</section>
		


<script>
function openSearchHelper() {
	var nHelpWin = newPopupWindow('http://www.kipris.or.kr/khome/help/help03/help03_1.jsp','HelpWin',820, 800, 'C', 'M', 'scrollbars=yes') ;
	nHelpWin.focus() ;
}
function openDictionary() {
	var nDictionaryWin = newPopupWindow('http://www.kipris.or.kr/khome/dictionary.do','dictionaryWin',750, 800, 'C', 'M', null) ;
	nDictionaryWin.focus() ;
}
</script>
<aside id="aside">
	<section>
		<ul class="straight">
			<li><a href="javascript:openSearchHelper()" title="새창으로 열립니다."><img src="/kportal/images/right/txt_straight01.gif" alt="검색도움말" /></a></li>
			<li><a href="javascript:void(newPopupWindow('http://www.kipris.or.kr/khome/guide/easy/glossary/glossary02.jsp','GlossaryWin',700, 690, 'R', 'M', 'scrollbars=yes'));" title="용어사전 새창으로 열림"><img src="/kportal/images/right/txt_straight02.gif" alt="용어사전"></a></li>
			<li><a href="http://www.kipris.or.kr/khome/guide/customer/suggestion.jsp"><img src="/kportal/images/right/txt_straight03.gif" alt="의견수렴" /></a></li>
		</ul>
	</section>
	<section class="realtime_searchword">
		<h2 class="float_left"><img src="/kportal/images/right/title_realtime.gif" alt="실시간인기검색어" /></h2>
		<p class="float_right"><a href="http://www.kipris.or.kr/khome/today/today.jsp"><img src="/kportal/images/right/btn_todayKipris.gif"  alt="Today KIPRIS" /></a></p>
		<ol class="folding_area" id="favorSearchWordListBoard">
		</ol>
	</section>
<script>

function setFavorSearchWordSearching(T, V) {
	jQuery("#searchKeyword").val(V) ;
	jQuery("#searchQueryInput").val(V) ;
	goTotalSearching() ;
}

function cutLongStr(str) {
	return (str.length > 10) ? str.substr(0,9) + "..." : str ;
}

function setFavorSearchWordList(xml, status) {
	jQuery("#favorSearchWordListBoard").empty() ;
	if (jQuery(xml).find("flag").text() == "SUCCESS") {
		if (parseInt(jQuery(xml).find("wordCount").text()) > 0) {
			var newTagStr = '<li><span class="rank"><em>{RANK}</em></span><a href="javascript:setFavorSearchWordSearching(\'{TYPE}\', \'{WORD_ORG}\')" title="{WORD_ORG}"><strong>{WORD}</strong></a><span class="blind {RANK_CHANGE_CSS}">{RANK_CHANGE_STR}</span><span class="num">{RANK_CHANGE_VAL}</span></li>' ;
			var rankLimit = 10 ;
			jQuery(xml).find("wordList").find("keyword").each(
				function() {
					if (parseInt(jQuery(this).find("wordRank").text()) <= rankLimit) {
						var addTagStr = newTagStr.replace(/{RANK}/g, jQuery(this).find("wordRank").text()) ;
						addTagStr = addTagStr.replace(/{TYPE}/g, jQuery(this).find("wordClass").text()) ;
						addTagStr = addTagStr.replace(/{WORD_ORG}/g, jQuery(this).find("word").text()) ;
						addTagStr = addTagStr.replace(/{WORD}/g, cutLongStr(jQuery(this).find("word").text())) ;
						if (jQuery(this).find("change").text() == "NEW") {
							addTagStr = addTagStr.replace(/{RANK_CHANGE_CSS}/, "new") ;
							addTagStr = addTagStr.replace(/{RANK_CHANGE_STR}/, "new") ;
							addTagStr = addTagStr.replace(/{RANK_CHANGE_VAL}/, "") ;
						} else {
							var rankChgN = parseInt(jQuery(this).find("change").text()) ;
							if (rankChgN < 0) {
								addTagStr = addTagStr.replace(/{RANK_CHANGE_CSS}/, "down") ;
								addTagStr = addTagStr.replace(/{RANK_CHANGE_STR}/, "하락") ;
								addTagStr = addTagStr.replace(/{RANK_CHANGE_VAL}/, Math.abs(rankChgN)) ;
							} else if (rankChgN > 0) {
								rankChgN = Math.abs(rankChgN) ;
								addTagStr = addTagStr.replace(/{RANK_CHANGE_CSS}/, "up") ;
								addTagStr = addTagStr.replace(/{RANK_CHANGE_STR}/, "상승") ;
								addTagStr = addTagStr.replace(/{RANK_CHANGE_VAL}/, rankChgN) ;
							} else {
								addTagStr = addTagStr.replace(/{RANK_CHANGE_CSS}/, "equal") ;
								addTagStr = addTagStr.replace(/{RANK_CHANGE_STR}/, "동일") ;
								addTagStr = addTagStr.replace(/{RANK_CHANGE_VAL}/, "") ;
							}
						}
						jQuery("#favorSearchWordListBoard").append(addTagStr) ;
					}
				}
			) ;
		} else {
			jQuery("#searchMore").hide() ;
		}
	} else {
		jQuery("#favorSearchWordListBoard").append("<li>인기검색어 데이타를 가져오는 도중 오류가 발생하였습니다.</li>") ;
	}
}

jQuery.ajax({
	type : "POST" ,
	dataType : "xml" ,
	url : "/kportal/remocon/viewStat/favorSearchWord.jsp" ,
	data : {
		C : "All"
		} ,
	success : function(xml, textStatus) {
		setFavorSearchWordList(xml, textStatus) ;
		} ,
	error : function(xhr, textStatus) {
	}
}) ;

</script>

	<!--section class="patent_area">
		<h2><img src="/kportal/images/right/title_patent.gif" alt="최근본특허" /></h2>
		<ul id="viewPatentHistoryList" class="patent_list">
			<li>1019940022509</li>
			<li>1019940022509</li>
			<li>1019940022509</li>
			<li>1019940022509</li>
			<li>1019940022509</li>
		</ul>
	</section-->
<form >

</form>
	<div><button type="button" id="goTopBtn" class="btn_top">TOP</button></div>
</aside>
<script>

var goTopBtnRollingId = null ;
function setGoTopBtnPosition() {
	if (!goTopBtnRollingId) {
		goTopBtnRollingId = window.setInterval(setGoTopBtnPosition, 5) ;
	}
	var newPos = (jQuery(document.documentElement).prop("clientHeight") / 2) - (jQuery("#goTopBtn").outerHeight(true) / 2) + ((jQuery(window).scrollTop() > jQuery("#body").offset().top) ? (jQuery(window).scrollTop() - jQuery("#body").offset().top) : (jQuery(window).scrollTop() - jQuery("#body").offset().top)) ;
	if (newPos < 10) newPos = 10 ;
	if (newPos > jQuery("#body").prop("clientHeight") - jQuery("#goTopBtn").outerHeight(true)) newPos = jQuery("#body").prop("clientHeight") - jQuery("#goTopBtn").outerHeight(true) ;
	if (newPos == jQuery("#goTopBtn").prop("offsetTop")) {
		if (goTopBtnRollingId)
			window.clearInterval(goTopBtnRollingId) ;
		goTopBtnRollingId = null ;
	} else {
		var movPos = parseInt(Math.abs(jQuery("#goTopBtn").prop("offsetTop") - newPos) * 0.2) ;
		if (jQuery("#goTopBtn").prop("offsetTop") < newPos) {
			jQuery("#goTopBtn").css("top", jQuery("#goTopBtn").prop("offsetTop") + movPos) ;
		} else {
			jQuery("#goTopBtn").css("top", jQuery("#goTopBtn").prop("offsetTop") - movPos) ;
		}
	}
}

jQuery("#goTopBtn").click(function() { document.location.href = "#" ; }) ;
setGoTopBtnPosition() ;
jQuery(window).resize(function() { setGoTopBtnPosition() ; }) ;
jQuery(window).scroll(function() { setGoTopBtnPosition() ; }) ;

</script>
	</div>



<footer id="footer">
	<div class="grab">
		<!--### 로고 ###-->
		<div class="flogo" id="flogo">
			<a href="http://www.kipo.go.kr" target="_blank" title="지식재산처 새창으로 열림"><img src="/kportal/images/footer/flogo01.png" alt="지식재산처" /></a>
			<a href="http://www.kipi.or.kr" target="_blank" title="한국특허정보원 새창으로 열림"><img src="/kportal/images/footer/flogo02.gif" alt="한국특허정보원" /></a>
		</div>
		
		<!--### 이용정책 메뉴 ###-->
		<ul class="fmenu">
			<li><a class="bold_point" href="https://www.kipo.go.kr/kipo/kipoContentView.do?menuCd=SCD0201359">개인정보처리방침</a></li>
			<li><a href="http://login.kipris.or.kr/member/kr/privacy/privacy01.jsp">이용약관</a></li>
			<li><a href="http://login.kipris.or.kr/member/kr/privacy/privacy03.jsp">저작권정책</a></li>
		</ul>
		
		<!--### 주소 ###-->
		<div class="fcenter">
			<div class="ftxt">
				<p>(우)35208 대전광역시 서구 청사로 189 (서구 둔산동 920번지) 정부대전청사 4동</p>
				<p>
					<span class="num"><b>산업재산권 제도·출원·심사·등록·수수료 등</b> 특허고객상담센터 : 1544-8080(유료)</span>
					&nbsp;&nbsp;
					<a href="https://chatbot.ips.go.kr/chatbotPop.ndo?bnrId=cuO6jXZLsIFMFrO" target="_blank" title="챗봇상담"><b>챗봇상담&nbsp;</b><img src="/kportal/images/footer/icon_newlayer.png" alt="새창" /></a>
                    <a href="https://chat.patent.go.kr:10443/#/ttalk_main/KIPO_160635643985448436" target="_blank" title="채팅상담"><b>채팅상담&nbsp;</b><img src="/kportal/images/footer/icon_newlayer.png" alt="새창" /></a>
                    <br>
                    <span class="num"><b>검색·시스템</b> 헬프데스크 042-483-4710(유료)</span> Copyrightⓒ KIPI. All rights reserved.
                </p>
			</div>
		</div>
		
		<!--### 웹접근성 로고 ###-->
		<div class="flogo02">
			<a href="http://www.wa.or.kr/board/list.asp?BoardID=0006" target="_blank" title="새창으로 열림"><img src="/kportal/images/footer/mark_acc_2023.png" style="width: 70px;" alt="(사)한국장애인단체총연합회 한국웹접근성인증평가원 웹 접근성 우수사이트 인증마크(WA인증마크)" /></a>
		</div>
	</div>
</footer>
</div>

<form name="searchResultPageFrm" id="searchResultPageFrm" method="post" action="/kportal/resulta.do">
	<input type="hidden" name="next" value="frnAUList" />
	<input type="hidden" id="searchResultQueryText" name="queryText" value="" />
	<input type="hidden" id="searchResultExpression" name="expression" value="" />
	<input type="hidden" id="searchResultSearchInTransKorToEng" name="searchInTransKorToEng" value="N" />
	<input type="hidden" id="searchResultSearchInTransEngToKor" name="searchInTransEngToKor" value="N" />
	<input type="hidden" id="searchResultSearchPage" name="page" value="1" />
        <input type="hidden" id="searchResultSearchPageNum" name="pageNum" value="3" />
</form>
<script>



function getNdslArticleSearchResult(K, E){
	setNdslArticleSearchResultCount(-1);
	jQuery.ajax({
		type : "POST" , dataType : "text" , url : "/kportal/search/search_ndsl.do" ,
		data : {
				doCount: 'ok'
				, displayCount: $('#opt28').val()
				, category: 'article'
				, query : K
				, queryText : K
				, expression : E
		} ,
		success : function(txt) { setNdslArticleSearchResultCount(parseInt(txt)) ; }
	}) ;
}
function getNdslJournalSearchResult(K, E){
	setNdslJournalSearchResultCount(-1);
	jQuery.ajax({
		type : "POST" , dataType : "text" , url : "/kportal/search/search_ndsl.do" ,
		data : {
				doCount: 'ok'
				, displayCount: $('#opt28').val()
				, category: 'journal'
				, query : K
				, queryText : K
				, expression : E
		} ,
		success : function(txt) { setNdslJournalSearchResultCount(parseInt(txt)) ; }
	}) ;
}

</script>
</body>
</html>