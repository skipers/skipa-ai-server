






    
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="X-UA-Compatible" content="ie=edge">
<!--  css Start -->
<link rel="stylesheet" href="/resource/css/common.css?v=2026052601">
<link rel="stylesheet" href="/resource/css/kipo_layout.css?v=2026052601">
<link rel="stylesheet" href="/resource/css/kipo_contents.css?v=2026052601">
<!--  js Start --> 
<script src="/resource/vendor/jquery/jquery.min.js"></script>
<script src="/resource/js/jquery-ui.min.js"></script>
<script src="/resource/js/kipo_ui.min.js"></script>

<title>지식재산처 > 지식재산제도 > 특허/실용신안 > 특허의 이해</title>
</head>
<body>
<!-- 본문바로가기 -->
<div id="skip"><a href="#content">본문 바로가기</a><a href="#gnb">주메뉴 바로가기</a></div>
<div id="wrap"> 
	<!-- header -->
<!--   <header id="header">  -->
		
    <!-- 헤더 상단 : s -->
    <!-- 2024.09.24, 전자점자 솔루션 호출 js 추가, KJH -->
<script src="/EDotXPressHtml/js/edotxpress-html.min.js?t=20240924"></script>
<script src="/EDotXPressHtml/js/edotxpress-common.js?t=20240924"></script>
<script src="/EDotXPressHtml/js/edotxpress-config-kipo.js?t=20240924"></script>
<script src="/resource/js/keywordValidator.js"></script>
<script>
function goLink(trgUrl, type){
	if(type == "10302"){
		window.open(trgUrl);
	}else{
		window.location.href=trgUrl;		
	}
}

function fn_search(){
	
	if($.trim($("#allsc").val())==""){
		alert("검색어를 입력해주세요.");
		$("#allsc").focus();
		return false;
	}

	document.searchHeadForm.query.value = $("#allsc").val();
	document.searchHeadForm.action = "/ko/searchView.do";
		
	//26.01.27.jnh 공공기관 웹사이트 불법광고 차단 요청으로 추가
	KeywordValidator.validateByForm("searchHeadForm", function() {
		document.searchHeadForm.submit();
	});
}

var link = document.querySelector("link[rel-='icon']");
if(!link){
	link = document.createElement('link');
	link.rel = 'icon';
	document.getElementsByTagName('head')[0].appendChild(link);
}
link.href = '/resource/images/favicon.ico';
	
</script>
<form id="searchHeadForm" name="searchHeadForm" method="post">
<!-- 23.08.24 검색 페이지 id 중복으로 id값 변경 -->
	<input type="hidden" name="query" id="query2">
</form>
<!-- 전자정부 누리집안내바 -->
<div class="eg_info">
		<p><img src="/resource/images/kipo_header_flag.png" alt="태극기">이 누리집은 대한민국 공식 전자정부 누리집입니다.</p>
</div>

<!-- 커튼 팝업 -->
<div class="headTop_bnr" id="b_close" style="display:none;">
	<div class="chk">
		<div class="layout">
			<input type="checkbox" title="오늘 하루이창 띄우지않기" id="chkNonOpenToday2" onclick="">
			<label for="chkNonOpenToday2" >오늘 하루 열지 않음</label>
			<a class="b_close" onclick="cotnPopClose()">닫기</a>
		</div>
	</div>
	<div class="bnr_area">
		<div class="list" id="cotnPopupList"></div>
	</div>
</div> 

<!-- header -->
	<header id="header">
		<div class="header_top">
			<div class="layout">
			<h1 class="logo"><a href="/ko"><img src="/resource/images/moip_logo.png?v=2025100101" alt="지식재산처"></a></h1>
				<div class="top_banner" id="bannerList">
					<img src="/ko/imgViewUrl.do?sysCd=SCD05&seq=6&jobGbn=B" alt="오늘의 아이디어 내일의 자산이 되다" title="오늘의 아이디어 내일의 자산이 되다">
							<a href="javascript:goLink('https://www.mois.go.kr/frt/sub/popup/p_taegugki_banner/screen.do','10302')" title="국가상징 알아보기 바로가기 (새창)">
									<img src="/ko/imgViewUrl.do?sysCd=SCD05&seq=3&jobGbn=B" alt="국가상징 알아보기 바로가기 (새창)">
								</a>
							</div>
				<div class="top_srch">
					<div class="ip_box">
						<label for="allsc" class="hide">통합검색</label>
						<input type="text" id="allsc" placeholder="검색어를 입력하세요." onkeydown="if((event.keyCode == 13)) {fn_search();}">
					</div>
					<button type="button" onclick="fn_search();">검색</button>
				</div>
				<div class="top_link">
					<!-- <a href="#" class="tlink_kcall">고객상담센터</a> -->
					<ul class="top_sns">
					    <li class="eng"><a href="/en/MainApp" target="_blank" title="바로가기 (새창)"><span class="">ENGLISH</span></a></li>
					    <li class="yt"><a href="https://www.youtube.com/@moipkorea" target="_blank" title="바로가기 (새창)"><span class="hide">지식재산처 유튜브</span></a></li>
						<li class="ins"><a href="https://www.instagram.com/moipkorea" target="_blank" title="바로가기 (새창)"><span class="hide">지식재산처 인스타그램</span></a></li>
						<li class="blog"><a href="https://blog.naver.com/moipkorea" target="_blank" title="바로가기 (새창)"><span class="hide">지식재산처 블로그</span></a></li>						
						<li class="fb"><a href="https://www.facebook.com/moipkorea" target="_blank" title="바로가기 (새창)"><span class="hide">지식재산처 페이스북</span></a></li>
						<li class="tw"><a href="https://x.com/moipkorea" target="_blank" title="바로가기 (새창)"><span class="hide">지식재산처 X</span></a></li>
					</ul>
				</div>
			</div>
		</div>
		<!-- 헤더 상단 : e --> 
		
	<!-- 헤더 하단 : s -->
	<div class="header_bottom">
	<div class="layout">

		<!-- gnb 메뉴 : s -->
		<nav id="gnbWrap">

		<h2 class="m_logo">
		<a href="/"><img src="/resource/images/moip_logo2.png?v=2025100101" alt="지식재산처"></a>
		</h2><span class="m_topba"><img src="/ko/imgViewUrl.do?sysCd=SCD05&seq=6&jobGbn=BM" alt="오늘의 아이디어 내일의 자산이 되다" title="오늘의 아이디어 내일의 자산이 되다"></span>
				<ul id="gnb">
			<li><a href="javascript:;"  ><span>소식알림</span></a>
				<div class="sub">
					<div class="m_inner">
						<div class="subM">
							<div class="subM_tit"><strong>소식알림</strong></div>
			<!-- 1depth child yes start -->
								 <!-- 2depth child yes start -->
									<div class="divide_box first">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200049" >알림사항</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200609&parntMenuCd2=SCD0200049"  >알림사항</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200610&parntMenuCd2=SCD0200049"  >고시공고</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0201381&parntMenuCd2=SCD0200049"  >IP지원사업</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200611&parntMenuCd2=SCD0200049"  >정보화사업 안내</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200612&parntMenuCd2=SCD0200049"  >인사동정</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200613"  >채용정보</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200050" >지식재산처뉴스</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/letter/kpoLetterPgmMgmt.do?menuCd=SCD0200656&parntMenuCd2=SCD0200050"  >정책소식지</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200615&parntMenuCd2=SCD0200050"  >사진뉴스</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0201222&parntMenuCd2=SCD0200050"  >카드뉴스</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200051" >인터넷공보</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoIframe.do?menuCd=SCD0200684"  >인터넷공보 안내</a></li>
												<li><a href="/ko/kpoIframe.do?menuCd=SCD0200685"  >기간별공보 조회</a></li>
												<li><a href="/ko/kpoIframe.do?menuCd=SCD0200686"  >특허실용신안</a></li>
												<li><a href="/ko/kpoIframe.do?menuCd=SCD0200687"  >디자인</a></li>
												<li><a href="/ko/kpoIframe.do?menuCd=SCD0200688"  >상표</a></li>
												<li><a href="/ko/kpoIframe.do?menuCd=SCD0200689"  >상표이미지 조회</a></li>
												<li><a href="/ko/kpoIframe.do?menuCd=SCD0200690"  >정정공보</a></li>
												<li><a href="/ko/kpoIframe.do?menuCd=SCD0200691"  >공시송달 등 기타공보</a></li>
												<li><a href="/ko/kpoIframe.do?menuCd=SCD0201171"  >공보의 주소 게재방식 변경 신청</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child no start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/kpoBultnMgmt.do?menuCd=SCD0201124&parntMenuCd2=SCD0200048" >지식재산처 주요성과</a>
												<ul></ul>
												</li>
										</ul>
									</div>
									 <!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200052" >보도자료</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200618&parntMenuCd2=SCD0200052"  >보도자료</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0201286&parntMenuCd2=SCD0200052"  >보도설명자료</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200619&parntMenuCd2=SCD0200052"  >주간 보도계획</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200053" >포상 및 행사</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200054"  >발명의날 기념식</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200101"  >특허기술상</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200102"  >대한민국 지식재산대전</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200104"  >올해의발명왕</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200108"  >대한민국 학생발명 전시회</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200622&parntMenuCd2=SCD0200053"  >정부포상 대상자 열람</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- CHECK -->
						</div>
					</div>
				</div>
			</li>
			<li><a href="javascript:;" class="active" ><span>지식재산제도</span></a>
				<div class="sub">
					<div class="m_inner">
						<div class="subM">
							<div class="subM_tit"><strong>지식재산제도</strong></div>
			<!-- 1depth child yes start -->
								 <!-- 2depth child yes start -->
									<div class="divide_box first">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200110" >특허/실용신안</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200111"  >특허의 이해</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200112"  >실용신안의 이해</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200113"  >특허심사3.0</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200146"  >심사기준</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200147"  >심사실무가이드</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200118"  >한국형 증거개시제도</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200119" >해외특허출원(PCT)</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200120"  >PCT 소개</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200133"  >PCT 서류작성 </a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200148"  >조회검색</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200151"  >자료실</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200152"  >새소식</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200153" >상표/디자인</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200154"  >상표의 이해</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200155"  >상표심사기준</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200156"  >디자인의 이해</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200157"  >디자인 심사기준</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200158"  >파리협약관련 공익표장</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200160"  >브렉시트와 상표디자인</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200161" >해외상표출원</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200162"  >마드리드 소개</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200166"  >국제출원절차</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200173"  >자료실</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200174" >해외디자인출원 </a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200175"  >헤이그 소개 </a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200176"  >국제출원 절차</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200177"  >국제사무국 절차</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200178"  >자료실</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200194" >산업재산권 등록제도</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200199"  >‘등록’이란?</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200197"  >등록신청 절차</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0201273"  >등록증</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0201276"  >연차/갱신 납부기간 안내서비스</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200205"  >자주 발생하는 오류 사항</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200206"  >자주 문의하는 사항</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200198"  >자료실</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200216" >주요제도</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200217"  >특허/실용신안 제도</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200241"  >상표/디자인 제도</a></li>
												<li><a href="https://www.patent.go.kr/smart/jsp/ka/menu/support/main/WipoAccessCodeHelp.do" target="_blank"  title="우선권증명서류 전자적 교환 제도 바로가기 (새창)" >우선권증명서류 전자적 교환 제도</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200258"  >산업재산분야 제도</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0201234" >인공지능과 발명</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0201260"  >대국민 설문조사 결과</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0201240"  >인공지능과 선진 5개 지식재산관청(IP5) 협력</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0201238"  >인공지능 발명자 이슈</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0201242"  >인공지능과 첨단기술 출원동향</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0201244"  >인공지능 발명의 특허요건과 기재요건</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200268" >분류코드조회</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200269"  >CPC 및 IPC 분류코드</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200270"  >한국형 혁신분류체계(KPC)</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200271"  >4차 산업혁명 관련 新특허분류 체계</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0201114"  >상품분류코드</a></li>
												<li><a href="/ko/dsgnSortMng.do?menuCd=SCD0201118&parntMenuCd2=SCD0200268"  >디자인분류코드</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200272"  >산업(KSIC)-특허(IPC) 연계표</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200273"  >기술-품목-특허 연계표</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200274" >인터넷 기술공지</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/tech/kpoTechNoticePgm.do?menuCd=SCD0200275&parntMenuCd2=SCD0200274"  >인터넷 기술공지 안내 및 신청</a></li>
												<li><a href="/ko/tech/kpoTechNoticePgmMgmt.do?menuCd=SCD0200657&parntMenuCd2=SCD0200274"  >인터넷 기술공지 자료실</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200276" >해외 주요 누리집</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200277"  >외국 특허담당 정부기관</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200278"  >국제 특허검색DB</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0201246"  >지식재산 진단</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- CHECK -->
						</div>
					</div>
				</div>
			</li>
			<li><a href="javascript:;"  ><span>책자/통계</span></a>
				<div class="sub">
					<div class="m_inner">
						<div class="subM">
							<div class="subM_tit"><strong>책자/통계</strong></div>
			<!-- 1depth child yes start -->
								 <!-- 2depth child yes start -->
									<div class="divide_box first">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200280" >법령 및 조약</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200286"  >지식재산권 법령체계도</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200637&parntMenuCd2=SCD0200280"  >최근개정법령</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200638&parntMenuCd2=SCD0200280"  >입법예고</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200639&parntMenuCd2=SCD0200280"  >최근 개정 훈령/예규/고시</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200287"  >국제조약 및 기타</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200290"  >고문변호사 소개</a></li>
												<li><a href="http://www.law.go.kr/main.html" target="_blank"  title="국가법령정보센터 바로가기 (새창)" >국가법령정보센터</a></li>
												<li><a href="https://elaw.klri.re.kr/kor_service/lawTotalSearchSogan.do" target="_blank"  title="대한민국 영문법령 바로가기 (새창)" >대한민국 영문법령</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200281" >간행물</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0201112&parntMenuCd2=SCD0200281"  >정책용역, 연구보고서</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0201119"  >지식재산 심사 기준/매뉴얼</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200292"  >지식재산 백서</a></li>
												<li><a href="/ko/issue/kpoIssuePgmMgmt.do?menuCd=SCD0200658&parntMenuCd2=SCD0200281"  >주요 발행물</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200640&parntMenuCd2=SCD0200281"  >기타 간행물</a></li>
												<li><a href="/ko/publication/kpoPublicationPgmMgmt.do?menuCd=SCD0200659&parntMenuCd2=SCD0200281"  >지식재산과 혁신/지식재산연구</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child no start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="http://library.kipo.go.kr/" class="blank" target="_blank" title="지식재산처 도서관 바로가기 (새창)">지식재산처 도서관</a>
												<ul></ul>
												</li>
										</ul>
									</div>
									 <!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200284" >통계</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200295"  >이번달 주요 통계</a></li>
												<li><a href="https://ipstat.kiip.re.kr/" target="_blank"  title="지식재산권 통계 바로가기 (새창)" >지식재산권 통계</a></li>
												<li><a href="/ko/stat/kpoStatPgmMgmt.do?menuCd=SCD0200661&parntMenuCd2=SCD0200284"  >통계 간행물</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0201290" >첨단전략산업 글로벌 기술동향과 특허</a>
												<ul class="subN2">
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0201291"  >글로벌 정책동향</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0201292"  >기술 분야별 동향</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0201306&parntMenuCd2=SCD0201290"  >지난 동향</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200285" >지식재산 동향</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200297"  >국내외지재권 동향</a></li>
												<li><a href="/ko/semi/kpoSemiPgmMgmt.do?menuCd=SCD0201133&parntMenuCd2=SCD0200285"  >반도체배치설계권 동향</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200642&parntMenuCd2=SCD0200285"  >의약관련특허 동향</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- CHECK -->
						</div>
					</div>
				</div>
			</li>
			<li><a href="javascript:;"  ><span>정책/업무</span></a>
				<div class="sub">
					<div class="m_inner">
						<div class="subM">
							<div class="subM_tit"><strong>정책/업무</strong></div>
			<!-- 1depth child yes start -->
								 <!-- 2depth child yes start -->
									<div class="divide_box first">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200301" >주요정책</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200305"  >주요업무계획</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200643&parntMenuCd2=SCD0200301"  >성과관리계획</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200644&parntMenuCd2=SCD0200301"  >평가자료실</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200302" >지원시책</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/sprtProjt.do?menuCd=SCD0200667&parntMenuCd2=SCD0200302"  >지원사업 조회</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200306"  >지식재산권창출지원</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200307"  >지식재산권활용지원</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200308"  >지식재산권보호지원</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200309"  >지식재산권금융지원</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200310"  >지식재산권교육·컨설팅지원</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200311"  >지식재산권행사지원</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200312"  >지식재산권기타지원</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200303" >규제개혁</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="https://www.sinmungo.go.kr" target="_blank"  title="규제개혁신문고 바로가기 (새창)" >규제개혁신문고</a></li>
												<li><a href="https://www.better.go.kr" target="_blank"  title="규제정보포털 바로가기 (새창)" >규제정보포털</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200645&parntMenuCd2=SCD0200303"  >규제개선 추진</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200383"  >규제입증요청창구</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200304" >적극행정</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200385"  >제도소개</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200646&parntMenuCd2=SCD0200304"  >알림/소식</a></li>
												<li><a href="https://www.mpm.go.kr/proactivePublicService/local/localCardNews/" target="_blank"  title="카드뉴스/웹툰/영상 바로가기 (새창)" >카드뉴스/웹툰/영상</a></li>
												<li><a href="https://www.mpm.go.kr/proactivePublicService/recommand/intro/" target="_blank"  title="공무원 정책 국민추천 바로가기 (새창)" >공무원 정책 국민추천</a></li>
												<li><a href="/ko/recommend/kpoRecommendPgm.do?menuCd=SCD0200388&parntMenuCd2=SCD0200304"  >지식재산처 공무원·정책 국민추천</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- CHECK -->
						</div>
					</div>
				</div>
			</li>
			<li><a href="javascript:;"  ><span>민원/참여</span></a>
				<div class="sub">
					<div class="m_inner">
						<div class="subM">
							<div class="subM_tit"><strong>민원/참여</strong></div>
			<!-- 1depth child yes start -->
								 <!-- 2depth child yes start -->
									<div class="divide_box first">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200390" class="blank" target="_blank" title="고객상담 바로가기 (새창)">고객상담</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="https://www.moip.go.kr/kcall" target="_blank"  title="특허고객상담센터 바로가기 (새창)" >특허고객상담센터</a></li>
												<li><a href="https://www.pcc.or.kr" target="_blank"  title="공익변리사 특허상담센터 바로가기 (새창)" >공익변리사 특허상담센터</a></li>
												<li><a href="https://www.110.go.kr/consult/cam.do" target="_blank"  title="110 수어상담 바로가기 (새창)" >110 수어상담</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child no start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/kpoContentView.do?menuCd=SCD0200394" >심사관 면담</a>
												<ul></ul>
												</li>
										</ul>
									</div>
									 <!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200395" >국민 신고</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200396"  >국민신문고</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0201157"  >산업재산침해 및 부정경쟁행위 신고</a></li>
												<li><a href="/ko/privacy/kpoPrivacyPgm.do?menuCd=SCD0200397&parntMenuCd2=SCD0200395"  >악의적 상표선점행위 피해신고</a></li>
												<li><a href="https://ncp.clean.go.kr/cmn/secCtfcKMC.do?menuCode=acs&mapAcs=Y&insttCd=1430000" target="_blank"  title="부패/공익신고 바로가기 (새창)" >부패/공익신고</a></li>
												<li><a href="/ko/badkpaa/kpoBadkpaaPgm.do?menuCd=SCD0200400&parntMenuCd2=SCD0200395"  >불성실 변리사 및 비 변리사 변리행위 신고</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0201349" >부정부패행위 신고</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/plcOfcCrpRptCntr.do?menuCd=SCD0201142&parntMenuCd2=SCD0201349"  >갑질·보조금 등 각종 비위 신고센터</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0201350"  >반부패 익명신고 채널</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200405" >지식재산처 정부혁신</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200406"  >제안안내</a></li>
												<li><a href="/ko/kpoIframe.do?menuCd=SCD0201106"  >제안신청</a></li>
												<li><a href="/ko/kpoIframe.do?menuCd=SCD0201107"  >공개제안, 우수제안</a></li>
												<li><a href="/ko/kpoIframe.do?menuCd=SCD0201108"  >나의제안</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200407" >국민신문고 정책참여 </a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoIframe.do?menuCd=SCD0201109"  >전자공청회</a></li>
												<li><a href="/ko/kpoIframe.do?menuCd=SCD0201110"  >설문조사</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0201197" >안전보건</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0201220"  >안전보건 목표</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0201198"  >안전보건 경영방침</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0201209"  >안전보건 의견함</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0201210&parntMenuCd2=SCD0201197"  >안전보건 자료실</a></li>
												<li><a href="https://www.safetyreport.go.kr/api?apiKey=143000087I9U9KKXL893MAV6AEQ" target="_blank"  title="안전신문고 바로가기 (새창)" >안전신문고</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child no start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/kpoContentView.do?menuCd=SCD0200408" >민원제도 개선</a>
												<ul></ul>
												</li>
										</ul>
									</div>
									 <!-- 2depth child no start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/cvcmpFrm.do?menuCd=SCD0201172&parntMenuCd2=SCD0200389" >민원서식</a>
												<ul></ul>
												</li>
										</ul>
									</div>
									 <!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200409" >기타 참여</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoIframe.do?menuCd=SCD0201111"  >고객서비스피드백</a></li>
												<li><a href="/ko/hpErrorRcpt.do?menuCd=SCD0201102&parntMenuCd2=SCD0200409"  >누리집 불편사항 접수</a></li>
												<li><a href="http://www.mpm.go.kr/mpm/info/compens/compens06" target="_blank"  title="공무원 마음건강센터 바로가기 (새창)" >공무원 마음건강센터</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- CHECK -->
						</div>
					</div>
				</div>
			</li>
			<li><a href="javascript:;"  ><span>정보공개</span></a>
				<div class="sub">
					<div class="m_inner">
						<div class="subM">
							<div class="subM_tit"><strong>정보공개</strong></div>
			<!-- 1depth child yes start -->
								 <!-- 2depth child yes start -->
									<div class="divide_box first">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200413" >즐겨찾는 정보 제공</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200647&parntMenuCd2=SCD0200413"  >주요 정보 공개</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0201356&parntMenuCd2=SCD0200413"  >국회업무보고</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200649&parntMenuCd2=SCD0200413"  >감사결과</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200648&parntMenuCd2=SCD0200413"  >업무추진비 사용내역</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0201362&parntMenuCd2=SCD0200413"  >온누리 상품권 구매 및 사용현황</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200651&parntMenuCd2=SCD0200413"  >공용차량 이용현황</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200652&parntMenuCd2=SCD0200413"  >계약현황</a></li>
												<li><a href="http://www.alio.go.kr" target="_blank"  title="산하기관 경영정보 바로가기 (새창)" >산하기관 경영정보</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child no start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/kpoContentView.do?menuCd=SCD0200414" >정보공개제도 안내</a>
												<ul></ul>
												</li>
										</ul>
									</div>
									 <!-- 2depth child no start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/kpoContentView.do?menuCd=SCD0200415" >비공개 대상 정보 세부기준</a>
												<ul></ul>
												</li>
										</ul>
									</div>
									 <!-- 2depth child no start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/kpoContentView.do?menuCd=SCD0200416" >정보공개 신청/확인</a>
												<ul></ul>
												</li>
										</ul>
									</div>
									 <!-- 2depth child no start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/befInfoOpn.do?menuCd=SCD0200417&parntMenuCd2=SCD0200412" >사전정보공개</a>
												<ul></ul>
												</li>
										</ul>
									</div>
									 <!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200418" >정보목록</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/infoApi.do?menuCd=SCD0201136&parntMenuCd2=SCD0200418"  >정보목록</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200653&parntMenuCd2=SCD0200418"  >(구)정보목록</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child no start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/kpoContentView.do?menuCd=SCD0200419" >공공데이터 이용</a>
												<ul></ul>
												</li>
										</ul>
									</div>
									 <!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200420" >정책실명제</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200654&parntMenuCd2=SCD0200420"  >정책실명제</a></li>
												<li><a href="/ko/realNameSysRqst.do?menuCd=SCD0200428&parntMenuCd2=SCD0200420"  >국민신청실명제</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200421" >재정정보공개</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/collectionApi.do?menuCd=SCD0201134&parntMenuCd2=SCD0200421"  >월별 수입 징수상황</a></li>
												<li><a href="/ko/excutionApi.do?menuCd=SCD0201135&parntMenuCd2=SCD0200421"  >월별 지출 집행상황</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200671"  >세입 사업별 설명자료</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200672"  >세출 사업별 설명자료</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200422" >국가보조금 공개</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200429"  >보조금 총괄현황</a></li>
												<li><a href="/ko/nopen/kpoNopenPgmMgmt.do?menuCd=SCD0200664&parntMenuCd2=SCD0200422"  >사업별 세부내용</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- CHECK -->
						</div>
					</div>
				</div>
			</li>
			<li><a href="javascript:;"  ><span>기관소개</span></a>
				<div class="sub">
					<div class="m_inner">
						<div class="subM">
							<div class="subM_tit"><strong>기관소개</strong></div>
			<!-- 1depth child yes start -->
								 <!-- 2depth child yes start -->
									<div class="divide_box first">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200431" >처장소개</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200437"  >인사말</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200438"  >프로필</a></li>
												<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200655&parntMenuCd2=SCD0200431"  >주요활동</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200439"  >역대 특허청장</a></li>
												<li><a href="/ko/introduce/drctrQstnMgmt.do?menuCd=SCD0200440&parntMenuCd2=SCD0200431"  >처장과의 대화</a></li>
												<li><a href="/ko/introduce/mainSchdlMgmt.do?menuCd=SCD0201122&parntMenuCd2=SCD0200431"  >주요일정</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200432" >일반현황</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200441"  >설립목적</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200442"  >주요연혁</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200443"  >기구 및 정원</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200444"  >임무/비전</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200445"  >예산</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200446"  >결산</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200433" >홍보관</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200447"  >지식재산처MI</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0201369"  >지식재산처 캐릭터</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200451"  >발명인의 전당</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200434" >조직소개</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/introduce/dpetInfoMgmt.do?menuCd=SCD0201147&parntMenuCd2=SCD0200434"  >본부</a></li>
												<li><a href="/ko/introduce/dpetInfoMgmtOrgB.do?menuCd=SCD0200457&parntMenuCd2=SCD0200434"  >소속기관</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200459"  >공직유관단체</a></li>
												<li><a href="http://www.gov.kr/portal/orgInfo" target="_blank"  title="정부/지자체 조직도 바로가기 (새창)" >정부/지자체 조직도</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200435" >명예의전당</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200461"  >심사명장 소개</a></li>
												<li><a href="/ko/topMenuLink.do?menuCd=SCD0200462"  >심사명장</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0200436" >찾아오시는 길</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200473"  >본부</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200474"  >서울사무소</a></li>
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0200475"  >층별배치도</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- 2depth child yes start -->
									<div class="divide_box">
										<ul>
										<li>
												<a href="/ko/topMenuLink.do?menuCd=SCD0201248" >누리집 도움말</a>
												<ul>
												<!-- 	                          					<ul> -->
												<li><a href="/ko/kpoContentView.do?menuCd=SCD0201249"  >이용안내</a></li>
												<li><a href="/ko/help/faqMgmt.do?menuCd=SCD0201252&parntMenuCd2=SCD0201248"  >자주 묻는 질문(FAQ)</a></li>
												</ul>
											</li>
										</ul>
									</div>
									<!-- CHECK -->
						</div>
					</div>
				</div>
			</li>
			<!-- 1depth loop end -->
			<li><a href="/ipt/" target="_blank" title="바로가기 (새창)"><span><img src="/resource/images/g_logo2.png?v=2025052201" alt="정부상징"> 특허심판원</span></a></li>
			<li><a href="https://www.patent.go.kr/" target="_blank" title="바로가기 (새창)"><span><img src="/resource/images/g_logo2.png?v=2025052201" alt="정부상징"> 특허로</span></a></li>	
			<li><a href="https://www.kipris.or.kr/" target="_blank" title="바로가기 (새창)"><span><img src="/resource/images/g_logo2.png?v=2025052201" alt="정부상징"> KIPRIS</span></a></li>
		</ul>

		</nav>
		<!-- gnb 메뉴 : e -->

		<ul class="etcMenu">
			<li><a class="hb_allM" href="/kipo/siteMap.do" target="_blank" title="바로가기 (새창)">전체메뉴 열기</a></li>
			<li><a class="mSch_btn" href="#popupM">통합검색 열기</a></li>
			<li><button type="button" class="mMenu_btn">메뉴 열기</button></li>
		</ul>

		</div>
	<div class="subM_Bg"></div>
	</div>
	</header>
    <!-- 헤더 하단 : e --> 
    
<!--   </header> -->
  <!-- 모바일메뉴 : s -->
  <script>
$(document).ready(function() {
	$.ajax({
		  type : "post",
		  contentType : "application/json",
		  url : "/ko/PopKeyWord.do",
		  dataType: 'json', 
		  data: JSON.stringify(),
		  success : function(data) {
			  let keywordList = data.POPKEYWORD; //서버에서 반환된 결과 배열
			  let listHtml = '';
			  for (let i = 0; i < keywordList.length; i++) { //자주찾는 검색어 리스트를 html로 생성해주기
				  listHtml += '<li><a href="#" onclick="$(\'#srchM\').val(\'' + keywordList[i] + '\'); fn_msearch();">' + (i + 1) + '. ' + keywordList[i] + '</a></li>';
			  }
			  $('#fv_list_M').html(listHtml); // 생성한 HTML을 리스트에 추가
	  	  },
	  		error : function(xhr) {
	      }
	});
	 
});
function fn_msearch(){
	
	if($.trim($("#srchM").val())==""){
		alert("검색어를 입력해주세요.");
		$("#srchM").focus();
		return false;
	}
	document.searchHeadForm.query.value = $("#srchM").val();
	document.searchHeadForm.action = "/ko/searchView.do";
	document.searchHeadForm.submit();
}
</script>
<!-- 23.08.22 id 중복오류로 popup1에서 popupM로 변경    -->
<div id="popupM" class="overlay">
	<div class="popup">
		<a class="close" href="#">&times;</a>
		<div class="content">
			<div class="bar_box">
			<!-- 23.08.22 id 중복오류로 srch에서 srch로 변경..    -->
				<label for="srchM" class="hide">통합검색</label>
				<input type="text" id="srchM" placeholder="찾으시는 검색어를 입력하세요." style="IME-MODE:active;" onkeydown="if((event.keyCode == 13)) {fn_msearch();}">
				<button type="button" onclick="fn_msearch();">검색</button>
			</div>
			<p>자주찾는 검색어</p> 
			<ul class="fv_list" id="fv_list_M">
			</ul>
		</div>
	</div>
</div>
  <nav id="mMenu">
    <div class="mMenu_mem">
      <ul>
      	<li class="eng"><a href="https://www.moip.go.kr/en/MainApp" title="바로가기 (새창)" target="_blank"><span class="">ENGLISH</span></a></li>
        <li class="m_sns yt"><a href="https://www.youtube.com/@moipkorea" title="바로가기 (새창)" target="_blank"><span class="hide">지식재산처 유튜브</span></a></li>
        <li class="m_sns ins"><a href="https://www.instagram.com/moipkorea" target="_blank" title="바로가기 (새창)"><span class="hide">지식재산처 인스타그램</span></a></li>
        <li class="m_sns blog"><a href="https://blog.naver.com/moipkorea" title="바로가기 (새창)" target="_blank"><span class="hide">지식재산처 블로그</span></a></li>
        <li class="m_sns fb"><a href="https://www.facebook.com/moipkorea" title="바로가기 (새창)" target="_blank"><span class="hide">지식재산처 페이스북</span></a></li>
        <li class="m_sns tw"><a href="https://x.com/moipkorea" title="바로가기 (새창)" target="_blank"><span class="hide">지식재산처 X</span></a></li>
      </ul>
    </div>
    
    <ul class="mMenu_list">
    
    	<!-- 1depth loop start -->
	    <li><a href="javascript:;">소식알림</a>
	    <ul>
            	<li><a href="javascript:;">알림사항</a><ul>
                        <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200609&parntMenuCd2=SCD0200049"  >알림사항</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200610&parntMenuCd2=SCD0200049"  >고시공고</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0201381&parntMenuCd2=SCD0200049"  >IP지원사업</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200611&parntMenuCd2=SCD0200049"  >정보화사업 안내</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200612&parntMenuCd2=SCD0200049"  >인사동정</a></li>
                            <li><a href="javascript:;">채용정보</a>
			              		<ul>
			              		<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0201203&parntMenuCd2=SCD0200613">채용공고</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201204">지식재산처 심사관 소개</a></li>
					            </ul>
			              	</li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">지식재산처뉴스</a><ul>
                        <li><a href="/ko/letter/kpoLetterPgmMgmt.do?menuCd=SCD0200656&parntMenuCd2=SCD0200050"  >정책소식지</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200615&parntMenuCd2=SCD0200050"  >사진뉴스</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0201222&parntMenuCd2=SCD0200050"  >카드뉴스</a></li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">인터넷공보</a><ul>
                        <li><a href="/ko/kpoIframe.do?menuCd=SCD0200684"  >인터넷공보 안내</a></li>
                            <li><a href="/ko/kpoIframe.do?menuCd=SCD0200685"  >기간별공보 조회</a></li>
                            <li><a href="/ko/kpoIframe.do?menuCd=SCD0200686"  >특허실용신안</a></li>
                            <li><a href="/ko/kpoIframe.do?menuCd=SCD0200687"  >디자인</a></li>
                            <li><a href="/ko/kpoIframe.do?menuCd=SCD0200688"  >상표</a></li>
                            <li><a href="/ko/kpoIframe.do?menuCd=SCD0200689"  >상표이미지 조회</a></li>
                            <li><a href="/ko/kpoIframe.do?menuCd=SCD0200690"  >정정공보</a></li>
                            <li><a href="/ko/kpoIframe.do?menuCd=SCD0200691"  >공시송달 등 기타공보</a></li>
                            <li><a href="/ko/kpoIframe.do?menuCd=SCD0201171"  >공보의 주소 게재방식 변경 신청</a></li>
                            </ul>
                        </li>
                    <li>
                          <a href="/ko/kpoBultnMgmt.do?menuCd=SCD0201124&parntMenuCd2=SCD0200048"  >지식재산처 주요성과</a>
                        </li>
                    <li><a href="javascript:;">보도자료</a><ul>
                        <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200618&parntMenuCd2=SCD0200052"  >보도자료</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0201286&parntMenuCd2=SCD0200052"  >보도설명자료</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200619&parntMenuCd2=SCD0200052"  >주간 보도계획</a></li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">포상 및 행사</a><ul>
                        <li><a href="/ko/kpoContentView.do?menuCd=SCD0200054"  >발명의날 기념식</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200101"  >특허기술상</a></li>
                            <li><a href="javascript:;">대한민국 지식재산대전</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0200103">대한민국 지식재산대전 개요</a></li>
					            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200620&parntMenuCd2=SCD0200102">포상 디렉토리</a></li>
					            </ul>
			              	</li>
                            <li><a href="javascript:;">올해의발명왕</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0200105">올해의 발명왕</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200106">발명대왕</a></li>
					            </ul>
			              	</li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200108"  >대한민국 학생발명 전시회</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200622&parntMenuCd2=SCD0200053"  >정부포상 대상자 열람</a></li>
                            </ul>
                        </li>
                    </ul>
            </li>
		<li><a href="javascript:;">지식재산제도</a>
	    <ul>
            	<li><a href="javascript:;">특허/실용신안</a><ul>
                        <li><a href="/ko/kpoContentView.do?menuCd=SCD0200111"  >특허의 이해</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200112"  >실용신안의 이해</a></li>
                            <li><a href="javascript:;">특허심사3.0</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0200114">특허심사 3.0 개요</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200116">일괄심사</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200117">보정안 리뷰</a></li>
					            </ul>
			              	</li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200146"  >심사기준</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200147"  >심사실무가이드</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200118"  >한국형 증거개시제도</a></li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">해외특허출원(PCT)</a><ul>
                        <li><a href="javascript:;">PCT 소개</a>
			              		<ul>
			              		<li><a href="/ko/topMenuLink.do?menuCd=SCD0200121">PCT국제출원제도 개요</a></li>
					            <li><a href="/ko/topMenuLink.do?menuCd=SCD0200126">PCT국제출원 절차</a></li>
					            <li><a href="/ko/topMenuLink.do?menuCd=SCD0200131">PCT 체약국 현황</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200132">관련기관 주소 및 연락처</a></li>
					            </ul>
			              	</li>
                            <li><a href="javascript:;">PCT 서류작성 </a>
			              		<ul>
			              		<li><a href="/ko/topMenuLink.do?menuCd=SCD0200134">국제출원서류 작성내용 및 요령</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200142">국제예비심사청구서 작성요령</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200143">주요 중간서류의 종류 및 작성</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200144">주요 통지서/요구서 등의 이해</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200145">PCT국제출원 수수료</a></li>
					            </ul>
			              	</li>
                            <li><a href="javascript:;">조회검색</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0200149">조회검색 서비스LINK</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200150">국제조사보고서 인용문헌LINK</a></li>
					            </ul>
			              	</li>
                            <li><a href="javascript:;">자료실</a>
			              		<ul>
			              		<li><a href="/ko/topMenuLink.do?menuCd=SCD0200623">PCT조약, 규칙, 가이드</a></li>
					            <li><a href="https://www.law.go.kr/lsSc.do?menuId=1&subMenuId=15&tabMenuId=81&query=%ED%8A%B9%ED%97%88%EB%B2%95#undefined">산업재산권 법령정보</a></li>
					            </ul>
			              	</li>
                            <li><a href="javascript:;">새소식</a>
			              		<ul>
			              		<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200626&parntMenuCd2=SCD0200152">고시/공지사항</a></li>
					            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200627&parntMenuCd2=SCD0200152">국제출원 소식지</a></li>
					            <li><a href="https://www.wipo.int/pct/en/texts/rule_changes_archive.html">개정 조약 및 규칙</a></li>
					            </ul>
			              	</li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">상표/디자인</a><ul>
                        <li><a href="/ko/kpoContentView.do?menuCd=SCD0200154"  >상표의 이해</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200155"  >상표심사기준</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200156"  >디자인의 이해</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200157"  >디자인 심사기준</a></li>
                            <li><a href="javascript:;">파리협약관련 공익표장</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0200159">열람</a></li>
					            <li><a href="/ko/parisConvention.do?menuCd=SCD0201141&parntMenuCd2=SCD0200158">검색</a></li>
					            </ul>
			              	</li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200160"  >브렉시트와 상표디자인</a></li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">해외상표출원</a><ul>
                        <li><a href="javascript:;">마드리드 소개</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0200163">상표의 해외출원방안</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200164">마드리드시스템</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200165">용어설명</a></li>
					            </ul>
			              	</li>
                            <li><a href="javascript:;">국제출원절차</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0200167">전자출원안내</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200168">서식작성요령</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200169">명의변경 절차</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200170">사후지정 절차</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200171">영문상품/서비스명 기재요령</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200172">수수료 계산 및 납부방법</a></li>
					            </ul>
			              	</li>
                            <li><a href="javascript:;">자료실</a>
			              		<ul>
			              		<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200628&parntMenuCd2=SCD0200173">마드리드 조약,규칙 및 간행물</a></li>
					            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200630&parntMenuCd2=SCD0200173">마드리드 소식</a></li>
					            </ul>
			              	</li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">해외디자인출원 </a><ul>
                        <li><a href="javascript:;">헤이그 소개 </a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0200179">헤이그 국제출원 개요</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200180">디자인의 국제출원 방법</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200181">헤이그 용어 설명</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200182">체약당사자 현황</a></li>
					            </ul>
			              	</li>
                            <li><a href="javascript:;">국제출원 절차</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0200183">지식재산처를 통한 전자출원</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200184">WIPO를 통한 전자출원</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200185">국제출원 서식작성 요령</a></li>
					            <li><a href="/ko/EnstcAtclNmSrch.do?menuCd=SCD0200621&parntMenuCd2=SCD0200176">영문 물품명칭 검색</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200186">수수료 계산 및 납부</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200187">중간서류의 작성 및 제출</a></li>
					            </ul>
			              	</li>
                            <li><a href="javascript:;">국제사무국 절차</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0200188">국제출원의 하자</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200189">국제등록의 공개</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200190">국제등록의 변경</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200191">국제등록의 갱신</a></li>
					            </ul>
			              	</li>
                            <li><a href="javascript:;">자료실</a>
			              		<ul>
			              		<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200631&parntMenuCd2=SCD0200178">헤이그협정/규칙/가이드</a></li>
					            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200632&parntMenuCd2=SCD0200178">간행물 자료</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200192">로카르노 분류</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200193">헤이그 FAQ</a></li>
					            </ul>
			              	</li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">산업재산권 등록제도</a><ul>
                        <li><a href="/ko/kpoContentView.do?menuCd=SCD0200199"  >‘등록’이란?</a></li>
                            <li><a href="javascript:;">등록신청 절차</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0201272">※ (공통안내) 신청서식 작성 및 제출 방법</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200207">[신규등록] 설정등록</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200208">[유지등록 (특허·실용신안·디자인권)] 연차등록</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200209">[유지등록 (상표권)] 존속기간갱신등록</a></li>
					            <li><a href="/ko/topMenuLink.do?menuCd=SCD0200210">변동등록</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200215">기타 등록신청</a></li>
					            </ul>
			              	</li>
                            <li><a href="javascript:;">등록증</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0201274">‘등록증’이란?</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201275">등록증 발급신청 방법</a></li>
					            </ul>
			              	</li>
                            <li><a href="javascript:;">연차/갱신 납부기간 안내서비스</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0200200">‘연차(갱신)등록 안내서비스’란?</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200204">연차등록 안내서비스 이용시 주의·의무사항</a></li>
					            </ul>
			              	</li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200205"  >자주 발생하는 오류 사항</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200206"  >자주 문의하는 사항</a></li>
                            <li><a href="javascript:;">자료실</a>
			              		<ul>
			              		<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200635&parntMenuCd2=SCD0200198">예규,지침</a></li>
					            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200636&parntMenuCd2=SCD0200198">첨부서류 양식</a></li>
					            </ul>
			              	</li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">주요제도</a><ul>
                        <li><a href="javascript:;">특허/실용신안 제도</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0200218">선행기술조사 전문기관 등록제도</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200219">국방출원관리</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200220">생명공학과 특허</a></li>
					            <li><a href="/ko/topMenuLink.do?menuCd=SCD0200221">서열목록 제출제도</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200222">미생물 기탁제도</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200223">허가등에 따른 특허권 존속기간 연장등록출원제도란?</a></li>
					            <li><a href="/ko/topMenuLink.do?menuCd=SCD0200224">특허 우선심사제도</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200227">특허심사하이웨이</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200228">지식재산관청간 특허 공동심사 프로그램(CSP)</a></li>
					            <li><a href="/ko/topMenuLink.do?menuCd=SCD0200229">영업방법(BM)특허</a></li>
					            <li><a href="/ko/topMenuLink.do?menuCd=SCD0200232">특허와 표준</a></li>
					            <li><a href="/ko/topMenuLink.do?menuCd=SCD0200235">IT특허분쟁</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200238">컴퓨터관련 발명</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200239">공지예외주장 제도</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200240">한국등록특허 효력인정제도</a></li>
					            </ul>
			              	</li>
                            <li><a href="javascript:;">상표/디자인 제도</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0200242">상표와 도메인</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200243">상표우선심사제도 소개</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200244">국내외 지리적 표시 제도</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200245">MADRID국제상표제도</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200246">상표법조약의 주요내용</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200247">국제상품분류(NICE분류)제도</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200248">디자인우선심사제도</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200250">비밀디자인제도</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200254">디자인분류</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200255">디자인일부심사등록제도</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200257">디자인 신속 심사 등록 제도</a></li>
					            </ul>
			              	</li>
                            <li><a href="https://www.patent.go.kr/smart/jsp/ka/menu/support/main/WipoAccessCodeHelp.do" target="_blank" title="우선권증명서류 전자적 교환 제도 바로가기(새창)"  class="m_blank1" >우선권증명서류 전자적 교환 제도</a></li>
                            <li><a href="javascript:;">산업재산분야 제도</a>
			              		<ul>
			              		<li><a href="/ko/topMenuLink.do?menuCd=SCD0200259">직무발명 보상제도</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200262">산업재산권 침해 권리보호</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200263">영업비밀 보호제도의 운영</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200264">변리사시험 운영,관리</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200265">강제실시제도</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200266">반도체 배치설계권</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200267">지식재산 경영인증</a></li>
					            </ul>
			              	</li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">인공지능과 발명</a><ul>
                        <li><a href="/ko/kpoContentView.do?menuCd=SCD0201260"  >대국민 설문조사 결과</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201240"  >인공지능과 선진 5개 지식재산관청(IP5) 협력</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201238"  >인공지능 발명자 이슈</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201242"  >인공지능과 첨단기술 출원동향</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201244"  >인공지능 발명의 특허요건과 기재요건</a></li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">분류코드조회</a><ul>
                        <li><a href="/ko/kpoContentView.do?menuCd=SCD0200269"  >CPC 및 IPC 분류코드</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200270"  >한국형 혁신분류체계(KPC)</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200271"  >4차 산업혁명 관련 新특허분류 체계</a></li>
                            <li><a href="javascript:;">상품분류코드</a>
			              		<ul>
			              		<li><a href="/ko/goodsSortMng.do?menuCd=SCD0201115&parntMenuCd2=SCD0201114">상품조회</a></li>
					            <li><a href="/ko/niceIntlGoodsSortMng.do?menuCd=SCD0201116&parntMenuCd2=SCD0201114">니스(NICE) 국제상품분류</a></li>
					            <li><a href="/ko/niceStd9IntlGoodsSortMng.do?menuCd=SCD0201117&parntMenuCd2=SCD0201114">상품해설서(NICE 13판 기준)</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201120">고시상품명칭/유사상품 심사기준(서비스업 유사군코드 해설서)</a></li>
					            <li><a href="/ko/similarGoodsNameMng.do?menuCd=SCD0201258&parntMenuCd2=SCD0201114">유사상품 명칭</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201121">주요국 상품 조회(검색)</a></li>
					            </ul>
			              	</li>
                            <li><a href="/ko/dsgnSortMng.do?menuCd=SCD0201118&parntMenuCd2=SCD0200268"  >디자인분류코드</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200272"  >산업(KSIC)-특허(IPC) 연계표</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200273"  >기술-품목-특허 연계표</a></li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">인터넷 기술공지</a><ul>
                        <li><a href="/ko/tech/kpoTechNoticePgm.do?menuCd=SCD0200275&parntMenuCd2=SCD0200274"  >인터넷 기술공지 안내 및 신청</a></li>
                            <li><a href="/ko/tech/kpoTechNoticePgmMgmt.do?menuCd=SCD0200657&parntMenuCd2=SCD0200274"  >인터넷 기술공지 자료실</a></li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">해외 주요 누리집</a><ul>
                        <li><a href="/ko/kpoContentView.do?menuCd=SCD0200277"  >외국 특허담당 정부기관</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200278"  >국제 특허검색DB</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201246"  >지식재산 진단</a></li>
                            </ul>
                        </li>
                    </ul>
            </li>
		<li><a href="javascript:;">책자/통계</a>
	    <ul>
            	<li><a href="javascript:;">법령 및 조약</a><ul>
                        <li><a href="/ko/kpoContentView.do?menuCd=SCD0200286"  >지식재산권 법령체계도</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200637&parntMenuCd2=SCD0200280"  >최근개정법령</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200638&parntMenuCd2=SCD0200280"  >입법예고</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200639&parntMenuCd2=SCD0200280"  >최근 개정 훈령/예규/고시</a></li>
                            <li><a href="javascript:;">국제조약 및 기타</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0200288">PCT</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200289">FTA 추진현황</a></li>
					            </ul>
			              	</li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200290"  >고문변호사 소개</a></li>
                            <li><a href="http://www.law.go.kr/main.html" target="_blank" title="국가법령정보센터 바로가기(새창)"  class="m_blank1" >국가법령정보센터</a></li>
                            <li><a href="https://elaw.klri.re.kr/kor_service/lawTotalSearchSogan.do" target="_blank" title="대한민국 영문법령 바로가기(새창)"  class="m_blank1" >대한민국 영문법령</a></li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">간행물</a><ul>
                        <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0201112&parntMenuCd2=SCD0200281"  >정책용역, 연구보고서</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201119"  >지식재산 심사 기준/매뉴얼</a></li>
                            <li><a href="javascript:;">지식재산 백서</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0200293">2025년 지식재산 백서</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200294">지난 백서보기</a></li>
					            </ul>
			              	</li>
                            <li><a href="/ko/issue/kpoIssuePgmMgmt.do?menuCd=SCD0200658&parntMenuCd2=SCD0200281"  >주요 발행물</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200640&parntMenuCd2=SCD0200281"  >기타 간행물</a></li>
                            <li><a href="/ko/publication/kpoPublicationPgmMgmt.do?menuCd=SCD0200659&parntMenuCd2=SCD0200281"  >지식재산과 혁신/지식재산연구</a></li>
                            </ul>
                        </li>
                    <li>
                          <a href="http://library.kipo.go.kr/"  class="m_blank1" target="_blank" title="지식재산처 도서관 바로가기(새창)">지식재산처 도서관</a>
                        </li>
                    <li><a href="javascript:;">통계</a><ul>
                        <li><a href="/ko/kpoContentView.do?menuCd=SCD0200295"  >이번달 주요 통계</a></li>
                            <li><a href="https://ipstat.kiip.re.kr/" target="_blank" title="지식재산권 통계 바로가기(새창)"  class="m_blank1" >지식재산권 통계</a></li>
                            <li><a href="/ko/stat/kpoStatPgmMgmt.do?menuCd=SCD0200661&parntMenuCd2=SCD0200284"  >통계 간행물</a></li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">첨단전략산업 글로벌 기술동향과 특허</a><ul>
                        <li><a href="/ko/kpoContentView.do?menuCd=SCD0201291"  >글로벌 정책동향</a></li>
                            <li><a href="javascript:;">기술 분야별 동향</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0201293">반도체</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201294">디스플레이</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201295">이차전지</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201297">첨단 모빌리티</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201298">차세대 원자력</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201296">첨단바이오</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201299">우주항공·해양</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201300">수소</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201301">사이버보안</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201302">인공지능</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201303">차세대통신</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201304">첨단로봇·제조</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201305">양자</a></li>
					            </ul>
			              	</li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0201306&parntMenuCd2=SCD0201290"  >지난 동향</a></li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">지식재산 동향</a><ul>
                        <li><a href="javascript:;">국내외지재권 동향</a>
			              		<ul>
			              		<li><a href="/ko/intProperty/kpoIntPropertyPgmMgmt.do?menuCd=SCD0201166&parntMenuCd2=SCD0200297">통계로 보는 특허동향</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200298">세계 지식재산동향</a></li>
					            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200641&parntMenuCd2=SCD0200297">해외지식재산센터(해외IP센터)자료</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200299">국외행사 정보</a></li>
					            </ul>
			              	</li>
                            <li><a href="/ko/semi/kpoSemiPgmMgmt.do?menuCd=SCD0201133&parntMenuCd2=SCD0200285"  >반도체배치설계권 동향</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200642&parntMenuCd2=SCD0200285"  >의약관련특허 동향</a></li>
                            </ul>
                        </li>
                    </ul>
            </li>
		<li><a href="javascript:;">정책/업무</a>
	    <ul>
            	<li><a href="javascript:;">주요정책</a><ul>
                        <li><a href="/ko/kpoContentView.do?menuCd=SCD0200305"  >주요업무계획</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200643&parntMenuCd2=SCD0200301"  >성과관리계획</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200644&parntMenuCd2=SCD0200301"  >평가자료실</a></li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">지원시책</a><ul>
                        <li><a href="/ko/sprtProjt.do?menuCd=SCD0200667&parntMenuCd2=SCD0200302"  >지원사업 조회</a></li>
                            <li><a href="javascript:;">지식재산권창출지원</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0200313">IP 디딤돌 프로그램</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200314">IP 나래 프로그램</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200315">글로벌 IP스타기업 육성</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200316">지재권 연계 연구개발 전략지원(특허로R&D)</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200318">표준특허 창출지원</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201213">정부 R&amp;D 우수특허 창출&middot;활용지원</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200321">국가 R&amp;D 특허동향 심층분석</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200322">생활발명코리아</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200323">지식재산 데이터 기프트 제도</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200324">지식재산 긴급지원</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200326">지식재산서비스 성장지원</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200328">산업재산진단기관 지정</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201167">소상공인 IP 창출지원</a></li>
					            </ul>
			              	</li>
                            <li><a href="javascript:;">지식재산권활용지원</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0200330">지식재산 거래 지원</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200339">아이디어 거래 지원</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200331">IP 사업화 연계 평가지원</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200332">우수발명품 우선구매 추천제도</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201217">공공 IP 사업화 지원</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200338">지식재산 수익 재투자 지원</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200336">공공기관 보유특허 진단 지원</a></li>
					            </ul>
			              	</li>
                            <li><a href="javascript:;">지식재산권보호지원</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0200340">영업비밀보호센터 운영</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200341">해외지식재산센터(해외IP센터) 운영</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200342">K-브랜드 보호기반 구축</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201373">지식재산보호 종합포털(IP-NAVI) 운영</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201374">수출도전기업 IP 분쟁대응 지원</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200344">특허분쟁 대응 지원</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200345">산업재산권 분쟁조정제도</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200350">지식재산 특별사법경찰 운영</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200346">위조상품 신고포상금제도 운영</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200348">지식재산권 허위표시 신고제도</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200349">부정경쟁행위 행정조사 및 시정권고</a></li>
					            </ul>
			              	</li>
                            <li><a href="javascript:;">지식재산권금융지원</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0200351">지식재산공제</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200352">IP담보대출 회수지원</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200353">IP 금융 연계 평가지원</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201367">우수특허 보유기업에 대한 벤처투자</a></li>
					            </ul>
			              	</li>
                            <li><a href="javascript:;">지식재산권교육·컨설팅지원</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0200354">지식재산(IP) 디지털 교육</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200358">지식재산기반 차세대영재기업인 육성</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200360">직무발명제도 컨설팅</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200362">특허지원 상담창구 운영</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200363">공익변리사 특허상담센터 운영</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200364">특허정보검색 및 전자출원 교육</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200366">발명교육센터 운영</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200367">IP 마이스터 프로그램</a></li>
					            </ul>
			              	</li>
                            <li><a href="javascript:;">지식재산권행사지원</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0200368">발명의 날 행사</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200369">대한민국 지식재산대전</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201228">여성발명왕EXPO</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200370">지식재산 데이터 활용 창업 경진대회</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200371">D2B 디자인페어</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200372">대한민국 학생 창의력 챔피언대회</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200373">특허기술상</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200374">대한민국 학생발명 전시회</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200375">캠퍼스 특허 유니버시아드</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201196">지식재산 스타트업 경진대회(IP리그)</a></li>
					            </ul>
			              	</li>
                            <li><a href="javascript:;">지식재산권기타지원</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0200376">직무발명보상 우수기업 인증</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200377">지식재산경영인증</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200378">수수료 감면제도</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200379">지식재산권 관련 조세 지원</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200380">특허심판-국선대리인 제도</a></li>
					            </ul>
			              	</li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">규제개혁</a><ul>
                        <li><a href="https://www.sinmungo.go.kr" target="_blank" title="규제개혁신문고 바로가기(새창)"  class="m_blank1" >규제개혁신문고</a></li>
                            <li><a href="https://www.better.go.kr" target="_blank" title="규제정보포털 바로가기(새창)"  class="m_blank1" >규제정보포털</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200645&parntMenuCd2=SCD0200303"  >규제개선 추진</a></li>
                            <li><a href="javascript:;">규제입증요청창구</a>
			              		<ul>
			              		<li><a href="/ko/prove/kpoProvePgm.do?menuCd=SCD0200384&parntMenuCd2=SCD0200383">규제입증요청</a></li>
					            <li><a href="/ko/prove/kpoProvePgmMgmt.do?menuCd=SCD0200662&parntMenuCd2=SCD0200383">요청현황</a></li>
					            <li><a href="/ko/prove/kpoProveYnPgmMgmt.do?menuCd=SCD0200663&parntMenuCd2=SCD0200383">입증대상규제</a></li>
					            </ul>
			              	</li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">적극행정</a><ul>
                        <li><a href="/ko/kpoContentView.do?menuCd=SCD0200385"  >제도소개</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200646&parntMenuCd2=SCD0200304"  >알림/소식</a></li>
                            <li><a href="https://www.mpm.go.kr/proactivePublicService/local/localCardNews/" target="_blank" title="카드뉴스/웹툰/영상 바로가기(새창)"  class="m_blank1" >카드뉴스/웹툰/영상</a></li>
                            <li><a href="https://www.mpm.go.kr/proactivePublicService/recommand/intro/" target="_blank" title="공무원 정책 국민추천 바로가기(새창)"  class="m_blank1" >공무원 정책 국민추천</a></li>
                            <li><a href="/ko/recommend/kpoRecommendPgm.do?menuCd=SCD0200388&parntMenuCd2=SCD0200304"  >지식재산처 공무원·정책 국민추천</a></li>
                            </ul>
                        </li>
                    </ul>
            </li>
		<li><a href="javascript:;">민원/참여</a>
	    <ul>
            	<li><a href="javascript:;">고객상담</a><ul>
                        <li><a href="https://www.moip.go.kr/kcall" target="_blank" title="특허고객상담센터 바로가기(새창)"  class="m_blank1" >특허고객상담센터</a></li>
                            <li><a href="https://www.pcc.or.kr" target="_blank" title="공익변리사 특허상담센터 바로가기(새창)"  class="m_blank1" >공익변리사 특허상담센터</a></li>
                            <li><a href="https://www.110.go.kr/consult/cam.do" target="_blank" title="110 수어상담 바로가기(새창)"  class="m_blank1" >110 수어상담</a></li>
                            </ul>
                        </li>
                    <li>
                          <a href="/ko/kpoContentView.do?menuCd=SCD0200394"  >심사관 면담</a>
                        </li>
                    <li><a href="javascript:;">국민 신고</a><ul>
                        <li><a href="/ko/kpoContentView.do?menuCd=SCD0200396"  >국민신문고</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201157"  >산업재산침해 및 부정경쟁행위 신고</a></li>
                            <li><a href="/ko/privacy/kpoPrivacyPgm.do?menuCd=SCD0200397&parntMenuCd2=SCD0200395"  >악의적 상표선점행위 피해신고</a></li>
                            <li><a href="https://ncp.clean.go.kr/cmn/secCtfcKMC.do?menuCode=acs&mapAcs=Y&insttCd=1430000" target="_blank" title="부패/공익신고 바로가기(새창)"  class="m_blank1" >부패/공익신고</a></li>
                            <li><a href="/ko/badkpaa/kpoBadkpaaPgm.do?menuCd=SCD0200400&parntMenuCd2=SCD0200395"  >불성실 변리사 및 비 변리사 변리행위 신고</a></li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">부정부패행위 신고</a><ul>
                        <li><a href="/ko/plcOfcCrpRptCntr.do?menuCd=SCD0201142&parntMenuCd2=SCD0201349"  >갑질·보조금 등 각종 비위 신고센터</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201350"  >반부패 익명신고 채널</a></li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">지식재산처 정부혁신</a><ul>
                        <li><a href="/ko/kpoContentView.do?menuCd=SCD0200406"  >제안안내</a></li>
                            <li><a href="/ko/kpoIframe.do?menuCd=SCD0201106"  >제안신청</a></li>
                            <li><a href="/ko/kpoIframe.do?menuCd=SCD0201107"  >공개제안, 우수제안</a></li>
                            <li><a href="/ko/kpoIframe.do?menuCd=SCD0201108"  >나의제안</a></li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">국민신문고 정책참여 </a><ul>
                        <li><a href="/ko/kpoIframe.do?menuCd=SCD0201109"  >전자공청회</a></li>
                            <li><a href="/ko/kpoIframe.do?menuCd=SCD0201110"  >설문조사</a></li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">안전보건</a><ul>
                        <li><a href="/ko/kpoContentView.do?menuCd=SCD0201220"  >안전보건 목표</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201198"  >안전보건 경영방침</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201209"  >안전보건 의견함</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0201210&parntMenuCd2=SCD0201197"  >안전보건 자료실</a></li>
                            <li><a href="https://www.safetyreport.go.kr/api?apiKey=143000087I9U9KKXL893MAV6AEQ" target="_blank" title="안전신문고 바로가기(새창)"  class="m_blank1" >안전신문고</a></li>
                            </ul>
                        </li>
                    <li>
                          <a href="/ko/kpoContentView.do?menuCd=SCD0200408"  >민원제도 개선</a>
                        </li>
                    <li>
                          <a href="/ko/cvcmpFrm.do?menuCd=SCD0201172&parntMenuCd2=SCD0200389"  >민원서식</a>
                        </li>
                    <li><a href="javascript:;">기타 참여</a><ul>
                        <li><a href="/ko/kpoIframe.do?menuCd=SCD0201111"  >고객서비스피드백</a></li>
                            <li><a href="/ko/hpErrorRcpt.do?menuCd=SCD0201102&parntMenuCd2=SCD0200409"  >누리집 불편사항 접수</a></li>
                            <li><a href="http://www.mpm.go.kr/mpm/info/compens/compens06" target="_blank" title="공무원 마음건강센터 바로가기(새창)"  class="m_blank1" >공무원 마음건강센터</a></li>
                            </ul>
                        </li>
                    </ul>
            </li>
		<li><a href="javascript:;">정보공개</a>
	    <ul>
            	<li><a href="javascript:;">즐겨찾는 정보 제공</a><ul>
                        <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200647&parntMenuCd2=SCD0200413"  >주요 정보 공개</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0201356&parntMenuCd2=SCD0200413"  >국회업무보고</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200649&parntMenuCd2=SCD0200413"  >감사결과</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200648&parntMenuCd2=SCD0200413"  >업무추진비 사용내역</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0201362&parntMenuCd2=SCD0200413"  >온누리 상품권 구매 및 사용현황</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200651&parntMenuCd2=SCD0200413"  >공용차량 이용현황</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200652&parntMenuCd2=SCD0200413"  >계약현황</a></li>
                            <li><a href="http://www.alio.go.kr" target="_blank" title="산하기관 경영정보 바로가기(새창)"  class="m_blank1" >산하기관 경영정보</a></li>
                            </ul>
                        </li>
                    <li>
                          <a href="/ko/kpoContentView.do?menuCd=SCD0200414"  >정보공개제도 안내</a>
                        </li>
                    <li>
                          <a href="/ko/kpoContentView.do?menuCd=SCD0200415"  >비공개 대상 정보 세부기준</a>
                        </li>
                    <li>
                          <a href="/ko/kpoContentView.do?menuCd=SCD0200416"  >정보공개 신청/확인</a>
                        </li>
                    <li>
                          <a href="/ko/befInfoOpn.do?menuCd=SCD0200417&parntMenuCd2=SCD0200412"  >사전정보공개</a>
                        </li>
                    <li><a href="javascript:;">정보목록</a><ul>
                        <li><a href="/ko/infoApi.do?menuCd=SCD0201136&parntMenuCd2=SCD0200418"  >정보목록</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200653&parntMenuCd2=SCD0200418"  >(구)정보목록</a></li>
                            </ul>
                        </li>
                    <li>
                          <a href="/ko/kpoContentView.do?menuCd=SCD0200419"  >공공데이터 이용</a>
                        </li>
                    <li><a href="javascript:;">정책실명제</a><ul>
                        <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200654&parntMenuCd2=SCD0200420"  >정책실명제</a></li>
                            <li><a href="/ko/realNameSysRqst.do?menuCd=SCD0200428&parntMenuCd2=SCD0200420"  >국민신청실명제</a></li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">재정정보공개</a><ul>
                        <li><a href="/ko/collectionApi.do?menuCd=SCD0201134&parntMenuCd2=SCD0200421"  >월별 수입 징수상황</a></li>
                            <li><a href="/ko/excutionApi.do?menuCd=SCD0201135&parntMenuCd2=SCD0200421"  >월별 지출 집행상황</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200671"  >세입 사업별 설명자료</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200672"  >세출 사업별 설명자료</a></li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">국가보조금 공개</a><ul>
                        <li><a href="/ko/kpoContentView.do?menuCd=SCD0200429"  >보조금 총괄현황</a></li>
                            <li><a href="/ko/nopen/kpoNopenPgmMgmt.do?menuCd=SCD0200664&parntMenuCd2=SCD0200422"  >사업별 세부내용</a></li>
                            </ul>
                        </li>
                    </ul>
            </li>
		<li><a href="javascript:;">기관소개</a>
	    <ul>
            	<li><a href="javascript:;">처장소개</a><ul>
                        <li><a href="/ko/kpoContentView.do?menuCd=SCD0200437"  >인사말</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200438"  >프로필</a></li>
                            <li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200655&parntMenuCd2=SCD0200431"  >주요활동</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200439"  >역대 특허청장</a></li>
                            <li><a href="/ko/introduce/drctrQstnMgmt.do?menuCd=SCD0200440&parntMenuCd2=SCD0200431"  >처장과의 대화</a></li>
                            <li><a href="/ko/introduce/mainSchdlMgmt.do?menuCd=SCD0201122&parntMenuCd2=SCD0200431"  >주요일정</a></li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">일반현황</a><ul>
                        <li><a href="/ko/kpoContentView.do?menuCd=SCD0200441"  >설립목적</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200442"  >주요연혁</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200443"  >기구 및 정원</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200444"  >임무/비전</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200445"  >예산</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200446"  >결산</a></li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">홍보관</a><ul>
                        <li><a href="/ko/kpoContentView.do?menuCd=SCD0200447"  >지식재산처MI</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201369"  >지식재산처 캐릭터</a></li>
                            <li><a href="javascript:;">발명인의 전당</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0200452">건립취지</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200453">관람안내</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200455">발명헌장</a></li>
					            </ul>
			              	</li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">조직소개</a><ul>
                        <li><a href="/ko/introduce/dpetInfoMgmt.do?menuCd=SCD0201147&parntMenuCd2=SCD0200434"  >본부</a></li>
                            <li><a href="/ko/introduce/dpetInfoMgmtOrgB.do?menuCd=SCD0200457&parntMenuCd2=SCD0200434"  >소속기관</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200459"  >공직유관단체</a></li>
                            <li><a href="http://www.gov.kr/portal/orgInfo" target="_blank" title="정부/지자체 조직도 바로가기(새창)"  class="m_blank1" >정부/지자체 조직도</a></li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">명예의전당</a><ul>
                        <li><a href="/ko/kpoContentView.do?menuCd=SCD0200461"  >심사명장 소개</a></li>
                            <li><a href="javascript:;">심사명장</a>
			              		<ul>
			              		<li><a href="/ko/kpoContentView.do?menuCd=SCD0201377">2025년 심사명장</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201347">2024년 심사명장</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201268">2023년 심사명장</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201224">2022년 심사명장</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0201153">2021년 심사명장</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200463">2020년 심사명장</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200464">2019년 심사명장</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200465">2018년 심사명장</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200466">2017년 심사명장</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200467">2016년 심사명장</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200468">2015년 심사명장</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200469">2014년 심사명장</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200470">2013년 심사명장</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200471">2012년 심사명장</a></li>
					            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200472">2011년 심사명장</a></li>
					            </ul>
			              	</li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">찾아오시는 길</a><ul>
                        <li><a href="/ko/kpoContentView.do?menuCd=SCD0200473"  >본부</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200474"  >서울사무소</a></li>
                            <li><a href="/ko/kpoContentView.do?menuCd=SCD0200475"  >층별배치도</a></li>
                            </ul>
                        </li>
                    <li><a href="javascript:;">누리집 도움말</a><ul>
                        <li><a href="/ko/kpoContentView.do?menuCd=SCD0201249"  >이용안내</a></li>
                            <li><a href="/ko/help/faqMgmt.do?menuCd=SCD0201252&parntMenuCd2=SCD0201248"  >자주 묻는 질문(FAQ)</a></li>
                            </ul>
                        </li>
                    </ul>
            </li>
		<li><a href="https://www.moip.go.kr/ipt/" title="특허심판원 바로가기(새창)" target="_blank" class="m_blank2">특허심판원</a></li>
	    <li><a href="https://www.patent.go.kr/" title="특허로 바로가기(새창)" target="_blank" class="m_blank2">특허로</a></li>	
		<li><a href="https://www.kipris.or.kr/" title="KIPRIS 바로가기(새창)" target="_blank" class="m_blank2">KIPRIS</a></li>
		
    </ul>
    <a href="#" class="mMenu_close">메뉴 닫기</a> </nav>
  
  <!-- 모바일메뉴 : e --> 
  
		<!-- //header E--> 
	<!-- container -->
	<div id="container">
		<div class="layout">
		
			<!-- Left메뉴 : s -->
			


<div id="lnb">
	<ul class="lnbMenu">
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- 2depth child yes start -->
		<li><a href="#" >특허/실용신안</a>
			<ul>
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200111"  class="on" >
           		특허의 이해</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200112"   >
           		실용신안의 이해</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes start -->
				<li><a href="SCD0200113" >특허심사3.0</a>
					<ul>
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200114"   >
	              		특허심사 3.0 개요</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200116"   >
	              		일괄심사</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200117"   >
	              		보정안 리뷰</a></li>
					
					
					<!-- 4depth loop end -->
					</ul>
				</li>
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200146"   >
           		심사기준</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200147"   >
           		심사실무가이드</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200118"   >
           		한국형 증거개시제도</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop end -->
			</ul>
		</li>
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- 2depth child yes start -->
		<li><a href="#" >해외특허출원(PCT)</a>
			<ul>
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes start -->
				<li><a href="SCD0200120" >PCT 소개</a>
					<ul>
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/topMenuLink.do?menuCd=SCD0200121"   >
	              		PCT국제출원제도 개요</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/topMenuLink.do?menuCd=SCD0200126"   >
	              		PCT국제출원 절차</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/topMenuLink.do?menuCd=SCD0200131"   >
	              		PCT 체약국 현황</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200132"   >
	              		관련기관 주소 및 연락처</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop end -->
					</ul>
				</li>
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes start -->
				<li><a href="SCD0200133" >PCT 서류작성 </a>
					<ul>
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/topMenuLink.do?menuCd=SCD0200134"   >
	              		국제출원서류 작성내용 및 요령</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200142"   >
	              		국제예비심사청구서 작성요령</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200143"   >
	              		주요 중간서류의 종류 및 작성</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200144"   >
	              		주요 통지서/요구서 등의 이해</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200145"   >
	              		PCT국제출원 수수료</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop end -->
					</ul>
				</li>
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes start -->
				<li><a href="SCD0200148" >조회검색</a>
					<ul>
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200149"   >
	              		조회검색 서비스LINK</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200150"   >
	              		국제조사보고서 인용문헌LINK</a></li>
					
					
					<!-- 4depth loop end -->
					</ul>
				</li>
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes start -->
				<li><a href="SCD0200151" >자료실</a>
					<ul>
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/topMenuLink.do?menuCd=SCD0200623"   >
	              		PCT조약, 규칙, 가이드</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="https://www.law.go.kr/lsSc.do?menuId=1&subMenuId=15&tabMenuId=81&query=%ED%8A%B9%ED%97%88%EB%B2%95#undefined" target="_blank" title="산업재산권 법령정보 바로가기(새창)"  >
	              		산업재산권 법령정보</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop end -->
					</ul>
				</li>
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes start -->
				<li><a href="SCD0200152" >새소식</a>
					<ul>
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200626&parntMenuCd2=SCD0200152"   >
	              		고시/공지사항</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200627&parntMenuCd2=SCD0200152"   >
	              		국제출원 소식지</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="https://www.wipo.int/pct/en/texts/rule_changes_archive.html" target="_blank" title="개정 조약 및 규칙 바로가기(새창)"  >
	              		개정 조약 및 규칙</a></li>
					
					
					<!-- 4depth loop end -->
					</ul>
				</li>
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop end -->
			</ul>
		</li>
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- 2depth child yes start -->
		<li><a href="#" >상표/디자인</a>
			<ul>
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200154"   >
           		상표의 이해</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200155"   >
           		상표심사기준</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200156"   >
           		디자인의 이해</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200157"   >
           		디자인 심사기준</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes start -->
				<li><a href="SCD0200158" >파리협약관련 공익표장</a>
					<ul>
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200159"   >
	              		열람</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/parisConvention.do?menuCd=SCD0201141&parntMenuCd2=SCD0200158"   >
	              		검색</a></li>
					
					
					<!-- 4depth loop end -->
					</ul>
				</li>
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200160"   >
           		브렉시트와 상표디자인</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop end -->
			</ul>
		</li>
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- 2depth child yes start -->
		<li><a href="#" >해외상표출원</a>
			<ul>
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes start -->
				<li><a href="SCD0200162" >마드리드 소개</a>
					<ul>
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200163"   >
	              		상표의 해외출원방안</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200164"   >
	              		마드리드시스템</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200165"   >
	              		용어설명</a></li>
					
					
					<!-- 4depth loop end -->
					</ul>
				</li>
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes start -->
				<li><a href="SCD0200166" >국제출원절차</a>
					<ul>
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200167"   >
	              		전자출원안내</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200168"   >
	              		서식작성요령</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200169"   >
	              		명의변경 절차</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200170"   >
	              		사후지정 절차</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200171"   >
	              		영문상품/서비스명 기재요령</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200172"   >
	              		수수료 계산 및 납부방법</a></li>
					
					
					<!-- 4depth loop end -->
					</ul>
				</li>
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes start -->
				<li><a href="SCD0200173" >자료실</a>
					<ul>
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200628&parntMenuCd2=SCD0200173"   >
	              		마드리드 조약,규칙 및 간행물</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200630&parntMenuCd2=SCD0200173"   >
	              		마드리드 소식</a></li>
					
					
					<!-- 4depth loop end -->
					</ul>
				</li>
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop end -->
			</ul>
		</li>
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- 2depth child yes start -->
		<li><a href="#" >해외디자인출원 </a>
			<ul>
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes start -->
				<li><a href="SCD0200175" >헤이그 소개 </a>
					<ul>
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200179"   >
	              		헤이그 국제출원 개요</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200180"   >
	              		디자인의 국제출원 방법</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200181"   >
	              		헤이그 용어 설명</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200182"   >
	              		체약당사자 현황</a></li>
					
					
					<!-- 4depth loop end -->
					</ul>
				</li>
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes start -->
				<li><a href="SCD0200176" >국제출원 절차</a>
					<ul>
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200183"   >
	              		지식재산처를 통한 전자출원</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200184"   >
	              		WIPO를 통한 전자출원</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200185"   >
	              		국제출원 서식작성 요령</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/EnstcAtclNmSrch.do?menuCd=SCD0200621&parntMenuCd2=SCD0200176"   >
	              		영문 물품명칭 검색</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200186"   >
	              		수수료 계산 및 납부</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200187"   >
	              		중간서류의 작성 및 제출</a></li>
					
					
					<!-- 4depth loop end -->
					</ul>
				</li>
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes start -->
				<li><a href="SCD0200177" >국제사무국 절차</a>
					<ul>
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200188"   >
	              		국제출원의 하자</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200189"   >
	              		국제등록의 공개</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200190"   >
	              		국제등록의 변경</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200191"   >
	              		국제등록의 갱신</a></li>
					
					
					<!-- 4depth loop end -->
					</ul>
				</li>
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes start -->
				<li><a href="SCD0200178" >자료실</a>
					<ul>
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200631&parntMenuCd2=SCD0200178"   >
	              		헤이그협정/규칙/가이드</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200632&parntMenuCd2=SCD0200178"   >
	              		간행물 자료</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200192"   >
	              		로카르노 분류</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200193"   >
	              		헤이그 FAQ</a></li>
					
					
					<!-- 4depth loop end -->
					</ul>
				</li>
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop end -->
			</ul>
		</li>
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- 2depth child yes start -->
		<li><a href="#" >산업재산권 등록제도</a>
			<ul>
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200199"   >
           		‘등록’이란?</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes start -->
				<li><a href="SCD0200197" >등록신청 절차</a>
					<ul>
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0201272"   >
	              		※ (공통안내) 신청서식 작성 및 제출 방법</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200207"   >
	              		[신규등록] 설정등록</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200208"   >
	              		[유지등록 (특허·실용신안·디자인권)] 연차등록</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200209"   >
	              		[유지등록 (상표권)] 존속기간갱신등록</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/topMenuLink.do?menuCd=SCD0200210"   >
	              		변동등록</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200215"   >
	              		기타 등록신청</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop end -->
					</ul>
				</li>
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes start -->
				<li><a href="SCD0201273" >등록증</a>
					<ul>
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0201274"   >
	              		‘등록증’이란?</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0201275"   >
	              		등록증 발급신청 방법</a></li>
					
					
					<!-- 4depth loop end -->
					</ul>
				</li>
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes start -->
				<li><a href="SCD0201276" >연차/갱신 납부기간 안내서비스</a>
					<ul>
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200200"   >
	              		‘연차(갱신)등록 안내서비스’란?</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200204"   >
	              		연차등록 안내서비스 이용시 주의·의무사항</a></li>
					
					
					<!-- 4depth loop end -->
					</ul>
				</li>
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200205"   >
           		자주 발생하는 오류 사항</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200206"   >
           		자주 문의하는 사항</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes start -->
				<li><a href="SCD0200198" >자료실</a>
					<ul>
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200635&parntMenuCd2=SCD0200198"   >
	              		예규,지침</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200636&parntMenuCd2=SCD0200198"   >
	              		첨부서류 양식</a></li>
					
					
					<!-- 4depth loop end -->
					</ul>
				</li>
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop end -->
			</ul>
		</li>
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- 2depth child yes start -->
		<li><a href="#" >주요제도</a>
			<ul>
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes start -->
				<li><a href="SCD0200217" >특허/실용신안 제도</a>
					<ul>
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200218"   >
	              		선행기술조사 전문기관 등록제도</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200219"   >
	              		국방출원관리</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200220"   >
	              		생명공학과 특허</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/topMenuLink.do?menuCd=SCD0200221"   >
	              		서열목록 제출제도</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200222"   >
	              		미생물 기탁제도</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200223"   >
	              		허가등에 따른 특허권 존속기간 연장등록출원제도란?</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/topMenuLink.do?menuCd=SCD0200224"   >
	              		특허 우선심사제도</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200227"   >
	              		특허심사하이웨이</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200228"   >
	              		지식재산관청간 특허 공동심사 프로그램(CSP)</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/topMenuLink.do?menuCd=SCD0200229"   >
	              		영업방법(BM)특허</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/topMenuLink.do?menuCd=SCD0200232"   >
	              		특허와 표준</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/topMenuLink.do?menuCd=SCD0200235"   >
	              		IT특허분쟁</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200238"   >
	              		컴퓨터관련 발명</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200239"   >
	              		공지예외주장 제도</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200240"   >
	              		한국등록특허 효력인정제도</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop end -->
					</ul>
				</li>
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes start -->
				<li><a href="SCD0200241" >상표/디자인 제도</a>
					<ul>
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200242"   >
	              		상표와 도메인</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200243"   >
	              		상표우선심사제도 소개</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200244"   >
	              		국내외 지리적 표시 제도</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200245"   >
	              		MADRID국제상표제도</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200246"   >
	              		상표법조약의 주요내용</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200247"   >
	              		국제상품분류(NICE분류)제도</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200248"   >
	              		디자인우선심사제도</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200250"   >
	              		비밀디자인제도</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200254"   >
	              		디자인분류</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200255"   >
	              		디자인일부심사등록제도</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200257"   >
	              		디자인 신속 심사 등록 제도</a></li>
					
					
					<!-- 4depth loop end -->
					</ul>
				</li>
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="https://www.patent.go.kr/smart/jsp/ka/menu/support/main/WipoAccessCodeHelp.do" target="_blank"  title="우선권증명서류 전자적 교환 제도 바로가기(새창)"  >
           		우선권증명서류 전자적 교환 제도</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes start -->
				<li><a href="SCD0200258" >산업재산분야 제도</a>
					<ul>
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/topMenuLink.do?menuCd=SCD0200259"   >
	              		직무발명 보상제도</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200262"   >
	              		산업재산권 침해 권리보호</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200263"   >
	              		영업비밀 보호제도의 운영</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200264"   >
	              		변리사시험 운영,관리</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200265"   >
	              		강제실시제도</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200266"   >
	              		반도체 배치설계권</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200267"   >
	              		지식재산 경영인증</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					<!-- 4depth loop end -->
					</ul>
				</li>
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop end -->
			</ul>
		</li>
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- 2depth child yes start -->
		<li><a href="#" >인공지능과 발명</a>
			<ul>
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0201260"   >
           		대국민 설문조사 결과</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0201240"   >
           		인공지능과 선진 5개 지식재산관청(IP5) 협력</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0201238"   >
           		인공지능 발명자 이슈</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0201242"   >
           		인공지능과 첨단기술 출원동향</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0201244"   >
           		인공지능 발명의 특허요건과 기재요건</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop end -->
			</ul>
		</li>
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- 2depth child yes start -->
		<li><a href="#" >분류코드조회</a>
			<ul>
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200269"   >
           		CPC 및 IPC 분류코드</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200270"   >
           		한국형 혁신분류체계(KPC)</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200271"   >
           		4차 산업혁명 관련 新특허분류 체계</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes start -->
				<li><a href="SCD0201114" >상품분류코드</a>
					<ul>
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/goodsSortMng.do?menuCd=SCD0201115&parntMenuCd2=SCD0201114"   >
	              		상품조회</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/niceIntlGoodsSortMng.do?menuCd=SCD0201116&parntMenuCd2=SCD0201114"   >
	              		니스(NICE) 국제상품분류</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/niceStd9IntlGoodsSortMng.do?menuCd=SCD0201117&parntMenuCd2=SCD0201114"   >
	              		상품해설서(NICE 13판 기준)</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0201120"   >
	              		고시상품명칭/유사상품 심사기준(서비스업 유사군코드 해설서)</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/similarGoodsNameMng.do?menuCd=SCD0201258&parntMenuCd2=SCD0201114"   >
	              		유사상품 명칭</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoContentView.do?menuCd=SCD0201121"   >
	              		주요국 상품 조회(검색)</a></li>
					
					
					<!-- 4depth loop end -->
					</ul>
				</li>
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/dsgnSortMng.do?menuCd=SCD0201118&parntMenuCd2=SCD0200268"   >
           		디자인분류코드</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200272"   >
           		산업(KSIC)-특허(IPC) 연계표</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200273"   >
           		기술-품목-특허 연계표</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop end -->
			</ul>
		</li>
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- 2depth child yes start -->
		<li><a href="#" >인터넷 기술공지</a>
			<ul>
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/tech/kpoTechNoticePgm.do?menuCd=SCD0200275&parntMenuCd2=SCD0200274"   >
           		인터넷 기술공지 안내 및 신청</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/tech/kpoTechNoticePgmMgmt.do?menuCd=SCD0200657&parntMenuCd2=SCD0200274"   >
           		인터넷 기술공지 자료실</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop end -->
			</ul>
		</li>
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- 2depth child yes start -->
		<li><a href="#" >해외 주요 누리집</a>
			<ul>
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200277"   >
           		외국 특허담당 정부기관</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200278"   >
           		국제 특허검색DB</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0201246"   >
           		지식재산 진단</a></li>
			<!-- 3depth child no end -->
			
			<!-- 3depth child yes end -->
			
			<!-- 3depth loop end -->
			</ul>
		</li>
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop end -->
	</ul>
</div>
			<!-- Left메뉴 : e -->
			
			<div id="content">
			
				<div class="locate">
					<h2 data-brl-use="PT">특허의 이해</h2>
					<ul class="location">
						<li class="home"><span><a href="/">HOME</a></span></li>
						
						<li class="depth1">
							<span>
							
								
									<a href="/ko/naviMenuLink.do?menuCd=SCD0200109">지식재산제도</a>
								
								
							
							</span>
						</li>
						
						<li class="depth1">
							<span>
							
								
									<a href="/ko/naviMenuLink.do?menuCd=SCD0200110">특허/실용신안</a>
								
								
							
							</span>
						</li>
						
						<li class="depth1">
							<span>
							
								
								특허의 이해
							
							</span>
						</li>
						
					</ul>
					
					<div class="locate_btn">
						<button class="sns_btn" onclick="sns()"><span class="hide">sns공유하기(페이스북,X,밴드,카카오스토리)</span><i class="fa fa-share-alt" title="sns공유하기"></i></button>
						<div class="sns_btns sns_btns_braille" id="sns"><!-- 점자전자서비스 버튼 아이콘 sns_btns_braille CSS 클래스 추가-->
							<a href="javascript:shareSNS('f','특허의 이해','/ko/kpoContentView.do?menuCd=SCD0200111');" title="페이스북 특허의 이해공유하기 새창 열림"><img src="/resource/images/sns_fb_b.png" alt="페이스북 공유하기 새창 열림"></a>
							<a href="javascript:shareSNS('t','특허의 이해','/ko/kpoContentView.do?menuCd=SCD0200111');" title="X 특허의 이해공유하기 새창 열림"><img src="/resource/images/sns_tw_b.png" alt="X 공유하기 새창 열림"></a>
							<a href="javascript:shareSNS('b','특허의 이해','/ko/kpoContentView.do?menuCd=SCD0200111');" title="밴드 특허의 이해공유하기 새창 열림"><img src="/resource/images/sns_blog_b.png" alt="밴드 공유하기 새창 열림"></a>
							<a href="javascript:shareSNS('k','특허의 이해','/ko/kpoContentView.do?menuCd=SCD0200111');" title="카카오스토리 특허의 이해공유하기 새창 열림"><img src="/resource/images/sns_kakao_b.png" alt="카카오스토리 공유하기 새창 열림"></a>
							<button class="close_btn" onclick="sns()"><i class="fa fa-times" title="SNS공유하기 닫기"></i><span class="hide">SNS공유하기 닫기</span></button>
						</div>
						
						
						
						<button class="print_btn" onclick="window.print()"><i class="fa fa-print" title="인쇄하기"></i></button>
					 	<button class="brailleviewer_btn" onclick="openBrlViewer('지식재산처 > 지식재산제도 > 특허/실용신안 > 특허의 이해')"><span class="fa braille_viewer" title="전자점자뷰어보기(새창열림)"></span></button>
						<button class="brailledown_btn" onclick="exportBrl('brl', '지식재산처 > 지식재산제도 > 특허/실용신안 > 특허의 이해')"><span class="fa braille_down" title="전자점자다운로드"></span></button> 
					</div>
					
				</div>
				<article class="txt">
				
					<!-- 5차 탭메뉴 : s -->
					
					<!-- 5차 탭메뉴 : e -->
					
          	<!-- 내용 : s -->
				<div class="page_con">
<h3 class="pt0">특허제도의 기원</h3>

<h4>특허제도의 기원</h4>

<div data-brl-use="PH">
<ul class="list_01">
	<li><strong>Patent의 어원(語源)</strong>

	<p class="ct3">14세기 영국에서 국왕이 특허권을 부여할 때, 다른 사람이 볼 수 있도록 개봉된 상태로 수여되었으므로 특허증서를 개봉된 문서, 즉 Letters Patent라 하였으며 그 후 &quot;Open&quot; 이라는 뜻을 가진 Patent가 특허권이라는 뜻으로 사용되게 되었음.</p>
	</li>
	<li><strong>최초의 특허법(1474년)</strong>
	<p class="ct3">르네상스 이후, 북부 이탈리아 도시국가 베니스에서 모직물공업 발전을 위해 법을 제정하여 제도적으로 발명을 보호 &rarr; 갈릴레오의 양수,관개용 기계에 대한 특허 (1594년)</p>
	</li>
	<li><strong>현대적 특허법의 모태</strong>
	<p class="ct3">영국의 전매조례 (Statute of Monopolies : 1624～1852) : 선발명주의, 독점권(14년), 공익위배 대상 특허 불인정 &rarr; 산업혁명의 근원이 되는 방적기, 증기기관 등이 탄생</p>
	</li>
</ul>

<h4>우리나라 특허제도의 연혁</h4>

<ul class="list_01">
	<li><strong>1908년 :</strong>한국 특허령 공포</li>
	<li><strong>1946년 :</strong>특허원 창립 및 특허법 제정</li>
	<li><strong>1961년 :</strong>특허법을 산업재산권 4법으로 분리</li>
	<li><strong>1977년 :</strong>특허청 개청</li>
	<li><strong>1979년 :</strong>세계지식재산권기구(WIPO) 가입</li>
	<li><strong>1980년 :</strong>파리협약(Paris Convention) 가입</li>
	<li><strong>1984년 :</strong>특허협력조약(Patent Cooperation Treaty) 가입</li>
</ul>

<h3>특허제도 개요</h3>

<h4>특허란</h4>

<ul class="list_01">
	<li><strong>특허제도의 목적</strong>

	<ul class="list_02">
		<li>특허제도는 발명을 보호&middot;장려함으로써 국가산업의 발전을 도모하기 위한 제도이며 (특허법 제1조) 이를 달성하기 위하여 「기술공개의 대가로 특허권을 부여」하는 것을 구체적인 수단으로 사용</li>
		<li>기술공개 &rarr; 기술축적, 공개기술 활용 &rarr; 산업발전</li>
		<li>독점권부여 &rarr; 사업화촉진, 발명의욕 고취 &rarr; 산업발전</li>
	</ul>
	</li>
	<li><strong>발명과 고안</strong>
	<ul class="list_02">
		<li>특허권은 발명에 대하여 부여하고 실용신안권은 고안에 대하여 부여</li>
		<li>특허법상 발명은 고안과 비교하여 고도한 것으로 정의</li>
		<li>발명: 자연법칙을 이용한 기술사상의 창작으로서 고도(高度)한 것</li>
		<li>고안: 자연법칙을 이용한 기술사상의 창작</li>
		<li>그러나 고도한 것이냐 아니냐 하는 것은 주관적인 판단이므로 심사실무적으로는 출원인에게 그 판단을 일임하고 있음. 즉, 출원인이 실용신안으로 출원한 것은 고안으로, 특허로 출원한 것은 발명으로 간주</li>
	</ul>
	</li>
	<li><strong>특허요건</strong>
	<ul class="list_02">
		<li>특허를 받기 위해서는 아래 요건을 모두 충족하여야 함</li>
		<li>(산업상 이용가능성) 출원발명은 산업에 이용할 수 있어야 함</li>
		<li>(신규성) 출원하기 전에 이미 알려진 기술(선행기술)이 아니어야 함</li>
		<li>(진보성) 선행기술과 다른 것이라 하더라도 그 선행기술로부터 쉽게 생각해 낼 수 없는 것이어야 함</li>
	</ul>
	</li>
	<li><strong>특허권의 효력</strong>
	<ul class="list_02 mb0">
		<li>특허권은 설정등록을 통해 효력 발생하며 존속기간은 출원일로부터 20년 (실용신안권 10년)</li>
		<li>권리를 획득한 국가 내에만 효력발생 (속지주의)</li>
	</ul>
	</li>
</ul>

<h4>선출원주의와 선발명주의</h4>

<p class="ct1">동일한 발명이 2 이상 출원되었을 때 어느 출원인에게 권리를 부여할 것인가를 결정하는 기준으로서 선출원주의와 선발명주의가 있으며 우리나라는 선출원주의를 채택하고 있음</p>

<ul class="list_01">
	<li><strong>선출원주의와 선발명주의</strong>

	<ul class="list_02">
		<li>동일한 발명이 2 이상 출원되었을 때 어느 출원인에게 권리를 부여할 것인가를 결정하는 기준으로서 선출원주의와 선발명주의가 있으며 우리나라는 선출원주의를 채택하고 있음</li>
	</ul>
	</li>
	<li><strong>선출원주의</strong>
	<ul class="list_02">
		<li>발명이 이루어진 시기에 관계없이 지식재산처에 먼저 출원한 발명에 귄리를 부여하는 것으로, 기술의 공개에 대한 대가로 권리를 부여한다는 의미에서 합리적이며 신속한 발명의 공개를 유도할 수 있어, 발명의 조속한 공개로 산업발전을 도모하려는 특허제도의 취지에 부합</li>
	</ul>
	</li>
	<li><strong>선발명주의</strong>
	<ul class="list_02">
		<li>출원의 순서와 관계없이 먼저 발명한 출원인에게 권리를 부여</li>
		<li>발명가 보호에 장점이 있음. 특히 사업체를 가지고 있지 않은 개인발명가들이 선호하는 제도</li>
		<li>발명가는 발명에 관련된 일지를 작성하고 증인을 확보해야 하며 지식재산처로서는 발명의 시기를 확인하여야 하는 불편이 있음</li>
	</ul>
	</li>
</ul>

<h4>특허를 받는 절차</h4>

<p class="ct1">[ 출원 &rarr; 심사 &rarr; 등록여부 결정 &rarr; (등록결정 시) 설정등록 ]<br />
*등록결정 이후 등록료까지 납부하여야 권한이 부여됨</p>

<h3>특허출원관련 안내</h3>

<h4>출원</h4>

<ul class="list_02">
	<li>특허를 받기 위하여 특허를 받을 권리를 가진 자 또는 그 승계인이 소정의 원서를 작성하여 지식재산처장에게 제출하는 것</li>
	<li><a class="btn add2" href="https://www.patent.go.kr/smart/jsp/ka/menu/guide/main/GuideMain02.do" target="_blank" title="출원 절차 및 양식 안내 (새창)바로 가기(특허로)">출원 절차 및 양식 안내 바로 가기(특허로)</a></li>
</ul>

<h4>출원서류의 구성</h4>

<ul class="list_01">
	<li>출원서 : 출원인, 대리인 및 발명(고안)의 명칭 등</li>
	<li>국적 및 거주국 기재시 2자리 영문코드로 기재<a class="btn add2 modal-open" href="#" title="국가 영문코드 목록">영문코드(클릭)</a>
	<div class="modal-wrapper" id="st_list">
	<div class="modal-bg">&nbsp;</div>

	<div class="modal-content">
	<div class="pop_title">
	<h3>국가목록</h3>
	<a class="pop_close modal-close" href="#">팝업 닫기</a></div>

	<div class="p_con">
	<div class="pop_boby">
	<table class="table_pop_ecode">
		<colgroup>
			<col style="width:40px" />
			<col style="width:auto" />
		</colgroup>
		<tbody>
			<tr>
				<td>1.</td>
				<td>(AD) Andorra</td>
			</tr>
			<tr>
				<td>2.</td>
				<td>(AE) United Arab Emirates</td>
			</tr>
			<tr>
				<td>3.</td>
				<td>(AF) Afghanistan</td>
			</tr>
			<tr>
				<td>4.</td>
				<td>(AG) Antigua and Barbuda</td>
			</tr>
			<tr>
				<td>5.</td>
				<td>(AI) Anguilla</td>
			</tr>
			<tr>
				<td>6.</td>
				<td>(AL) Albania</td>
			</tr>
			<tr>
				<td>7.</td>
				<td>(AM) Armenia</td>
			</tr>
			<tr>
				<td>8.</td>
				<td>(AN) Netherlands Antilles</td>
			</tr>
			<tr>
				<td>9.</td>
				<td>(AO) Angola</td>
			</tr>
			<tr>
				<td>10.</td>
				<td>(AP) ARIPO</td>
			</tr>
			<tr>
				<td>11.</td>
				<td>(AR) Argentina</td>
			</tr>
			<tr>
				<td>12.</td>
				<td>(AS) American Samoa</td>
			</tr>
			<tr>
				<td>13.</td>
				<td>(AT) Austria</td>
			</tr>
			<tr>
				<td>14.</td>
				<td>(AU) Australia</td>
			</tr>
			<tr>
				<td>15.</td>
				<td>(AW) Aruba</td>
			</tr>
			<tr>
				<td>16.</td>
				<td>(AZ) Azerbaijan</td>
			</tr>
			<tr>
				<td>17.</td>
				<td>(BA) Bosnia and Herzegovina</td>
			</tr>
			<tr>
				<td>18.</td>
				<td>(BB) Barbados</td>
			</tr>
			<tr>
				<td>19.</td>
				<td>(BD) Bangladesh</td>
			</tr>
			<tr>
				<td>20.</td>
				<td>(BE) Belgium</td>
			</tr>
			<tr>
				<td>21.</td>
				<td>(BF) Burkina Faso</td>
			</tr>
			<tr>
				<td>22.</td>
				<td>(BG) Bulgaria</td>
			</tr>
			<tr>
				<td>23.</td>
				<td>(BH) Bahrain</td>
			</tr>
			<tr>
				<td>24.</td>
				<td>(BI) Burundi</td>
			</tr>
			<tr>
				<td>25.</td>
				<td>(BJ) Benin</td>
			</tr>
			<tr>
				<td>26.</td>
				<td>(BM) Bermuda</td>
			</tr>
			<tr>
				<td>27.</td>
				<td>(BN) Burnei Darussalam</td>
			</tr>
			<tr>
				<td>28.</td>
				<td>(BO) Bolivia</td>
			</tr>
			<tr>
				<td>29.</td>
				<td>(BR) Brazil</td>
			</tr>
			<tr>
				<td>30.</td>
				<td>(BS) Bahamas</td>
			</tr>
			<tr>
				<td>31.</td>
				<td>(BT) Bhutan</td>
			</tr>
			<tr>
				<td>32.</td>
				<td>(BV) Bouvet Island</td>
			</tr>
			<tr>
				<td>33.</td>
				<td>(BW) Botswana</td>
			</tr>
			<tr>
				<td>34.</td>
				<td>(BY) Belarus</td>
			</tr>
			<tr>
				<td>35.</td>
				<td>(BZ) Belize</td>
			</tr>
			<tr>
				<td>36.</td>
				<td>(CA) Canada</td>
			</tr>
			<tr>
				<td>37.</td>
				<td>(CF) Central African Republic</td>
			</tr>
			<tr>
				<td>38.</td>
				<td>(CG) Congo</td>
			</tr>
			<tr>
				<td>39.</td>
				<td>(CH) Switzerland</td>
			</tr>
			<tr>
				<td>40.</td>
				<td>(CI) Cote d&#39;Ivoire</td>
			</tr>
			<tr>
				<td>41.</td>
				<td>(CK) Cook Islands</td>
			</tr>
			<tr>
				<td>42.</td>
				<td>(CL) Chile</td>
			</tr>
			<tr>
				<td>43.</td>
				<td>(CM) Cameroon</td>
			</tr>
			<tr>
				<td>44.</td>
				<td>(CN) China</td>
			</tr>
			<tr>
				<td>45.</td>
				<td>(CO) Colombia</td>
			</tr>
			<tr>
				<td>46.</td>
				<td>(CR) Costa Rica</td>
			</tr>
			<tr>
				<td>47.</td>
				<td>(CU) Cuba</td>
			</tr>
			<tr>
				<td>48.</td>
				<td>(CV) Cape Verde</td>
			</tr>
			<tr>
				<td>49.</td>
				<td>(CY) Cyprus</td>
			</tr>
			<tr>
				<td>50.</td>
				<td>(CZ) Czech Republic</td>
			</tr>
			<tr>
				<td>51.</td>
				<td>(DE) Germany</td>
			</tr>
			<tr>
				<td>52.</td>
				<td>(DJ) Djibouti</td>
			</tr>
			<tr>
				<td>53.</td>
				<td>(DK) Denmark</td>
			</tr>
			<tr>
				<td>54.</td>
				<td>(DM) Dominica</td>
			</tr>
			<tr>
				<td>55.</td>
				<td>(DO) Dominican Republic</td>
			</tr>
			<tr>
				<td>56.</td>
				<td>(DZ) Algeria</td>
			</tr>
			<tr>
				<td>57.</td>
				<td>(EA) Eurasian patent Organization(EAPO)</td>
			</tr>
			<tr>
				<td>58.</td>
				<td>(EC) Ecuador</td>
			</tr>
			<tr>
				<td>59.</td>
				<td>(EE) Estonia</td>
			</tr>
			<tr>
				<td>60.</td>
				<td>(EG) Egypt</td>
			</tr>
			<tr>
				<td>61.</td>
				<td>(EH) Western Sahara</td>
			</tr>
			<tr>
				<td>62.</td>
				<td>(EM) OHIM</td>
			</tr>
			<tr>
				<td>63.</td>
				<td>(EP) EPO</td>
			</tr>
			<tr>
				<td>64.</td>
				<td>(ER) Eritrea</td>
			</tr>
			<tr>
				<td>65.</td>
				<td>(ES) Spain</td>
			</tr>
			<tr>
				<td>66.</td>
				<td>(ET) Ethiopia</td>
			</tr>
			<tr>
				<td>67.</td>
				<td>(FI) Finland</td>
			</tr>
			<tr>
				<td>68.</td>
				<td>(FJ) Fiji</td>
			</tr>
			<tr>
				<td>69.</td>
				<td>(FK) Falkland Islands(Malvinas)</td>
			</tr>
			<tr>
				<td>70.</td>
				<td>(FM) Micronesia(Federated States of Micronesia)</td>
			</tr>
			<tr>
				<td>71.</td>
				<td>(FO) Faroe Islands</td>
			</tr>
			<tr>
				<td>72.</td>
				<td>(FR) France</td>
			</tr>
			<tr>
				<td>73.</td>
				<td>(GA) Gabon</td>
			</tr>
			<tr>
				<td>74.</td>
				<td>(GB) United Kingdom</td>
			</tr>
			<tr>
				<td>75.</td>
				<td>(GD) Grenada</td>
			</tr>
			<tr>
				<td>76.</td>
				<td>(GE) Georgia</td>
			</tr>
			<tr>
				<td>77.</td>
				<td>(GH) Ghana</td>
			</tr>
			<tr>
				<td>78.</td>
				<td>(GI) Gibraltar</td>
			</tr>
			<tr>
				<td>79.</td>
				<td>(GL) Greenland</td>
			</tr>
			<tr>
				<td>80.</td>
				<td>(GM) Gambia</td>
			</tr>
			<tr>
				<td>81.</td>
				<td>(GN) Guinea</td>
			</tr>
			<tr>
				<td>82.</td>
				<td>(GQ) Equatorial Guniea</td>
			</tr>
			<tr>
				<td>83.</td>
				<td>(GR) Greece</td>
			</tr>
			<tr>
				<td>84.</td>
				<td>(GS) South Georgia and the south Sandwich Islands</td>
			</tr>
			<tr>
				<td>85.</td>
				<td>(GT) Guatemala</td>
			</tr>
			<tr>
				<td>86.</td>
				<td>(GW) Guinea-Bissau</td>
			</tr>
			<tr>
				<td>87.</td>
				<td>(GY) Guyana</td>
			</tr>
			<tr>
				<td>88.</td>
				<td>(HK) Hong Kong</td>
			</tr>
			<tr>
				<td>89.</td>
				<td>(HN) Honduras</td>
			</tr>
			<tr>
				<td>90.</td>
				<td>(HR) Croatia</td>
			</tr>
			<tr>
				<td>91.</td>
				<td>(HT) Haiti</td>
			</tr>
			<tr>
				<td>92.</td>
				<td>(HU) Hungary</td>
			</tr>
			<tr>
				<td>93.</td>
				<td>(IB) International Bureau of the world Intellectual Property Organization(WIPO)</td>
			</tr>
			<tr>
				<td>94.</td>
				<td>(ID) Indonesia</td>
			</tr>
			<tr>
				<td>95.</td>
				<td>(IE) Ireland</td>
			</tr>
			<tr>
				<td>96.</td>
				<td>(IL) Israel</td>
			</tr>
			<tr>
				<td>97.</td>
				<td>(IN) India</td>
			</tr>
			<tr>
				<td>98.</td>
				<td>(IQ) Iraq</td>
			</tr>
			<tr>
				<td>99.</td>
				<td>(IR) Iran(Islamic Republic of)</td>
			</tr>
			<tr>
				<td>100.</td>
				<td>(IS) Iceland</td>
			</tr>
			<tr>
				<td>101.</td>
				<td>(IT) Italy</td>
			</tr>
			<tr>
				<td>102.</td>
				<td>(JM) Jamaica</td>
			</tr>
			<tr>
				<td>103.</td>
				<td>(JO) Jordan</td>
			</tr>
			<tr>
				<td>104.</td>
				<td>(JP) Japan</td>
			</tr>
			<tr>
				<td>105.</td>
				<td>(KE) Kenya</td>
			</tr>
			<tr>
				<td>106.</td>
				<td>(KG) Kyrgyzstan</td>
			</tr>
			<tr>
				<td>107.</td>
				<td>(KN) Saint Kitts and Nevis</td>
			</tr>
			<tr>
				<td>108.</td>
				<td>(KP) Democratic People&#39;s Republic of Korea</td>
			</tr>
			<tr>
				<td>109.</td>
				<td>(KR) Republic of Korea</td>
			</tr>
			<tr>
				<td>110.</td>
				<td>(KW) Kuwait</td>
			</tr>
			<tr>
				<td>111.</td>
				<td>(KY) Cayman Islands</td>
			</tr>
			<tr>
				<td>112.</td>
				<td>(KZ) Kazakstan</td>
			</tr>
			<tr>
				<td>113.</td>
				<td>(LA) Laos</td>
			</tr>
			<tr>
				<td>114.</td>
				<td>(LB) Lebanon</td>
			</tr>
			<tr>
				<td>115.</td>
				<td>(LC) Saint Lucia</td>
			</tr>
			<tr>
				<td>116.</td>
				<td>(LI) Liechtenstein</td>
			</tr>
			<tr>
				<td>117.</td>
				<td>(LK) Sri Lanka</td>
			</tr>
			<tr>
				<td>118.</td>
				<td>(LR) Liberia</td>
			</tr>
			<tr>
				<td>119.</td>
				<td>(LS) Lesotho</td>
			</tr>
			<tr>
				<td>120.</td>
				<td>(LT) Lithuania</td>
			</tr>
			<tr>
				<td>121.</td>
				<td>(LU) Luxembourg</td>
			</tr>
			<tr>
				<td>122.</td>
				<td>(LV) Latvia</td>
			</tr>
			<tr>
				<td>123.</td>
				<td>(LY) Libya</td>
			</tr>
			<tr>
				<td>124.</td>
				<td>(MA) Morocco</td>
			</tr>
			<tr>
				<td>125.</td>
				<td>(MC) Monaco</td>
			</tr>
			<tr>
				<td>126.</td>
				<td>(MD) Republic of Moldova</td>
			</tr>
			<tr>
				<td>127.</td>
				<td>(MG) Madagascar</td>
			</tr>
			<tr>
				<td>128.</td>
				<td>(ML) Mali</td>
			</tr>
			<tr>
				<td>129.</td>
				<td>(MM) Myanmar</td>
			</tr>
			<tr>
				<td>130.</td>
				<td>(MN) Mongolia</td>
			</tr>
			<tr>
				<td>131.</td>
				<td>(MO) Macau</td>
			</tr>
			<tr>
				<td>132.</td>
				<td>(MP) Northern Mariana Islands</td>
			</tr>
			<tr>
				<td>133.</td>
				<td>(MR) Mauritania</td>
			</tr>
			<tr>
				<td>134.</td>
				<td>(MS) Montserrat</td>
			</tr>
			<tr>
				<td>135.</td>
				<td>(MT) Malta</td>
			</tr>
			<tr>
				<td>136.</td>
				<td>(MU) Mauritius</td>
			</tr>
			<tr>
				<td>137.</td>
				<td>(MV) Maldives</td>
			</tr>
			<tr>
				<td>138.</td>
				<td>(MW) Malawi</td>
			</tr>
			<tr>
				<td>139.</td>
				<td>(MX) Mexico</td>
			</tr>
			<tr>
				<td>140.</td>
				<td>(MY) Malaysia</td>
			</tr>
			<tr>
				<td>141.</td>
				<td>(MZ) Mozambique</td>
			</tr>
			<tr>
				<td>142.</td>
				<td>(NA) Namibia</td>
			</tr>
			<tr>
				<td>143.</td>
				<td>(NE) Niger</td>
			</tr>
			<tr>
				<td>144.</td>
				<td>(NG) Nigeria</td>
			</tr>
			<tr>
				<td>145.</td>
				<td>(NI) Nicaragua</td>
			</tr>
			<tr>
				<td>146.</td>
				<td>(NL) Netherlands</td>
			</tr>
			<tr>
				<td>147.</td>
				<td>(NO) Norway</td>
			</tr>
			<tr>
				<td>148.</td>
				<td>(NR) Nauru</td>
			</tr>
			<tr>
				<td>149.</td>
				<td>(NZ) New Zealand</td>
			</tr>
			<tr>
				<td>150.</td>
				<td>(OA) African Intellectual Property Organization(OAPI)</td>
			</tr>
			<tr>
				<td>151.</td>
				<td>(OM) Oman</td>
			</tr>
			<tr>
				<td>152.</td>
				<td>(PA) Panama</td>
			</tr>
			<tr>
				<td>153.</td>
				<td>(PE) Peru</td>
			</tr>
			<tr>
				<td>154.</td>
				<td>(PG) Papua New Guinea</td>
			</tr>
			<tr>
				<td>155.</td>
				<td>(PH) Philippines</td>
			</tr>
			<tr>
				<td>156.</td>
				<td>(PK) Pakistan</td>
			</tr>
			<tr>
				<td>157.</td>
				<td>(PL) Poland</td>
			</tr>
			<tr>
				<td>158.</td>
				<td>(PT) Portugal</td>
			</tr>
			<tr>
				<td>159.</td>
				<td>(PY) Paraguay</td>
			</tr>
			<tr>
				<td>160.</td>
				<td>(QA) Qatar</td>
			</tr>
			<tr>
				<td>161.</td>
				<td>(RO) Romania</td>
			</tr>
			<tr>
				<td>162.</td>
				<td>(RU) Russian Federation</td>
			</tr>
			<tr>
				<td>163.</td>
				<td>(RW) Rwanda</td>
			</tr>
			<tr>
				<td>164.</td>
				<td>(SA) Saudi Arabia</td>
			</tr>
			<tr>
				<td>165.</td>
				<td>(SB) Solomon Islands</td>
			</tr>
			<tr>
				<td>166.</td>
				<td>(SC) Seychelles</td>
			</tr>
			<tr>
				<td>167.</td>
				<td>(SD) Sudan</td>
			</tr>
			<tr>
				<td>168.</td>
				<td>(SE) Sweden</td>
			</tr>
			<tr>
				<td>169.</td>
				<td>(SG) Singapore</td>
			</tr>
			<tr>
				<td>170.</td>
				<td>(SH) Saint Helena</td>
			</tr>
			<tr>
				<td>171.</td>
				<td>(SI) Slovenia</td>
			</tr>
			<tr>
				<td>172.</td>
				<td>(SK) Slovakia</td>
			</tr>
			<tr>
				<td>173.</td>
				<td>(SL) Sierra Leone</td>
			</tr>
			<tr>
				<td>174.</td>
				<td>(SM) San Marino</td>
			</tr>
			<tr>
				<td>175.</td>
				<td>(SN) Senegal</td>
			</tr>
			<tr>
				<td>176.</td>
				<td>(SO) Somalia</td>
			</tr>
			<tr>
				<td>177.</td>
				<td>(SR) Suriname</td>
			</tr>
			<tr>
				<td>178.</td>
				<td>(ST) Sao Tome and Principe</td>
			</tr>
			<tr>
				<td>179.</td>
				<td>(SV) EI Salvador</td>
			</tr>
			<tr>
				<td>180.</td>
				<td>(SY) Syria</td>
			</tr>
			<tr>
				<td>181.</td>
				<td>(SZ) Swaziland</td>
			</tr>
			<tr>
				<td>182.</td>
				<td>(TC) Turks and Caicos Islands</td>
			</tr>
			<tr>
				<td>183.</td>
				<td>(TD) Chad</td>
			</tr>
			<tr>
				<td>184.</td>
				<td>(TG) Togo</td>
			</tr>
			<tr>
				<td>185.</td>
				<td>(TH) Thailand</td>
			</tr>
			<tr>
				<td>186.</td>
				<td>(TJ) Tajikistan</td>
			</tr>
			<tr>
				<td>187.</td>
				<td>(TM) Turkmenistan</td>
			</tr>
			<tr>
				<td>188.</td>
				<td>(TN) Tunisia</td>
			</tr>
			<tr>
				<td>189.</td>
				<td>(TO) Tonga</td>
			</tr>
			<tr>
				<td>190.</td>
				<td>(TP) East Timor</td>
			</tr>
			<tr>
				<td>191.</td>
				<td>(TR) Turkey</td>
			</tr>
			<tr>
				<td>192.</td>
				<td>(TT) Trinidad and Tobago</td>
			</tr>
			<tr>
				<td>193.</td>
				<td>(TV) Tuvalu</td>
			</tr>
			<tr>
				<td>194.</td>
				<td>(TW) Taiwan, Province of China</td>
			</tr>
			<tr>
				<td>195.</td>
				<td>(TZ) United Republic of Tanzania</td>
			</tr>
			<tr>
				<td>196.</td>
				<td>(UA) Ukraine</td>
			</tr>
			<tr>
				<td>197.</td>
				<td>(UG) Uganda</td>
			</tr>
			<tr>
				<td>198.</td>
				<td>(US) United States of America</td>
			</tr>
			<tr>
				<td>199.</td>
				<td>(UY) Uruguay</td>
			</tr>
			<tr>
				<td>200.</td>
				<td>(UZ) Uzbekistan</td>
			</tr>
			<tr>
				<td>201.</td>
				<td>(VA) Holy See</td>
			</tr>
			<tr>
				<td>202.</td>
				<td>(VC) Saint Vincent and the Grenadines</td>
			</tr>
			<tr>
				<td>203.</td>
				<td>(VE) Venezuela</td>
			</tr>
			<tr>
				<td>204.</td>
				<td>(VG) Virgin Islands(British)</td>
			</tr>
			<tr>
				<td>205.</td>
				<td>(VN) Viet Nam</td>
			</tr>
			<tr>
				<td>206.</td>
				<td>(VU) Vanuatu</td>
			</tr>
			<tr>
				<td>207.</td>
				<td>(WS) Samoa</td>
			</tr>
			<tr>
				<td>208.</td>
				<td>(YE) Yemen</td>
			</tr>
			<tr>
				<td>209.</td>
				<td>(YU) Yugoslavia</td>
			</tr>
			<tr>
				<td>210.</td>
				<td>(ZA) South Africa</td>
			</tr>
			<tr>
				<td>211.</td>
				<td>(ZM) Zambia</td>
			</tr>
			<tr>
				<td>212.</td>
				<td>(ZR) Zaire</td>
			</tr>
			<tr>
				<td>213.</td>
				<td>(ZW) Zimbabwe</td>
			</tr>
		</tbody>
	</table>
	</div>

	<div class="pop_bottom">
	<div class="btnAreaLR">
	<div class="btnA_c"><a class="btn blue2 modal-close" href="#" id="pClose">창닫기</a></div>
	</div>
	</div>
	</div>
	</div>
	</div>
	</li>
	<li>명세서 : 발명의 설명, 청구범위(특허발명의 보호범위)</li>
	<li>도면 : 필요한 경우 기술구성을 도시하여 발명을 명확히 표현</li>
	<li>요약서 : 발명을 요약정리 (기술정보로 활용)</li>
</ul>

<h3>특허심사 관련 안내</h3>

<h4>심사절차</h4>

<ul class="list_01">
	<li>심사절차는 방식심사 &rarr; 출원공개 &rarr; 실체심사 &rarr; 특허결정 &rarr; 등록공고로 5가지로 이루어져 있습니다.</li>
	<li><strong>방식심사</strong>는 출원의 주체,법령이 정한 방식상 요건 등 절차의 흠결 유무를 점검합니다.</li>
	<li><strong>출원공개</strong>는 특허출원에 대하여 그 출원일로부터 1년 6개월이 경과한 때 또는 출원인의 신청이 있는 때는 기술 내용을 공개 공보에 개재하여 일반인에게 공개합니다.</li>
	<li><strong>실체심사</strong>는 발명의 내용파악, 선행기술 조사등을 통해 특허여부를 판단 합니다.</li>
	<li><strong>특허결정</strong>은 심사결과 거절이유가 존재하지 않을 때에는 특허결정서를 출원인에게 통지합니다.</li>
	<li><strong>등록공고</strong>는 특허결정되어 특허권이 설정 등록되면 그 내용을 일반인에게 공개합니다.</li>
</ul>

<h4 class="pb15">특허출원 후 심사 흐름도</h4>

<div class="cimg">
<figure><img alt="특허출원 후 심사 흐름도" src="/resource/images/patent/right_01.png" />
<figcaption>출원(특법 제42조) 후 방식심사를 하는데 출원 후 1년6개월이 되면 출원공개(특법 제64조)를 합니다 이는 특법 제 64조에 해당됩니다. 방식심사는 출원의 주체,법령이 정한 방식상 요건 등 절차의 흠결 유무를 점검합니다. 심사청구가 통과 되면 실체심사를 하고 거절이유 유무에서 거절이유가 있으면 의견제출통지서(거절이유통지)를 받으며 거절이유해소를 위해 의견서나 보정서를 제출하여 해소를 하실 수 있습니다. 거절이유 해소에서 해소가 되지 못한다면 거절이 결정되며 재심사를 청구할 수 있고 거절결정불복심판청구를 하실 수 있습니다. 이는 특법 62조에 해당됩니다. 거절결정불복심판청구(거절결정불복심판청구조문제132조의 17)에서는 2가지 선택으로 나뉘며 취소심결(환송)(특법 제176조)을 하여 실체심사를 다시 하는 것과 기각심결을 하여 특허법원에서 확인받는 방법이 있습니다. 거절이유유무에서 거절이 되지않으면 특허결정이 됩니다. 이는 특법 제66조에 해당됩니다. 특허결정후 설정등록과 등록공고를 합니다. 이는 특법 제87조에 해당됩니다. 설정등록과 등록공고후 무효심판청구를 합니다. 이는 특법 제133조에 해당됩니다. 무효심판청구에서는 기각심결과 인용심결로 나뉩니다 이는 특법 제 162조에 해당됩니다. 그 후 특허법원을 거쳐 대법원에서 심사됩니다. 이는 특법 제 186조에 해당됩니다.</figcaption>
</figure>
</div>
<a class="btn line cbtn" href="/resource/images/patent/right_01.png" target="_blank" title="특허출원 후 심사 흐름도 큰 이미지로 보기(새창)">큰 이미지로 보기</a>

<h4>특허법</h4>
<a class="btn line2 mb10" href="http://www.law.go.kr/lsSc.do?menuId=0&amp;p1=&amp;subMenu=1&amp;query=%ED%8A%B9%ED%97%88&amp;x=0&amp;y=0" target="_blank" title="특허법 보기(새창)">특허법 보기</a>

<h4>주요 절차 설명</h4>

<ul class="list_01">
	<li><strong>방식심사</strong>

	<ul class="list_02">
		<li>서식의 필수사항 기재 여부, 기간의 준수여부, 증명서 첨부 여부, 수수료 납부 여부 등 절차상의 흠결을 점검하는 심사</li>
		<li><a class="btn add2 modal-open" href="#" title="방식심사 흐름도">방식심사 흐름도(클릭)</a>
		<div class="modal-wrapper" id="f01">
		<div class="modal-bg">&nbsp;</div>

		<div class="modal-content">
		<div class="pop_title">
		<h3>방식심사 흐름도</h3>
		<a class="pop_close modal-close" href="#">팝업 닫기</a></div>

		<div class="p_con">
		<div class="pop_boby">
		<div class="img-wrap">
		<figure><img alt="방식심사흐름도" src="/resource/images/patent/patent_img200902.png" />
		<figcaption>특허출원 후 흠결유무에서 흠결이 없다면 실체심사를 하고 흠결이 있다면 보정요구 및 반려이유통지 합니다. 보정사항 유무 판단은 다음과 같습니다. 절차능력 유무 여부 ,절차무능력자에 의한 절차,무권대리,서식 기재 방법 준수,첨부서류 제출 여부,수수료 납부 여부,법정수수료의 적정납부 반려사항 유무 판단은 다음과 같습니다. 출원종류가 명확한가?,법정기간 경과하여 제출된 서류인가?,재외자가 특허관리인을 통해 절차를 밟았는가?, 일정기간내에 연장등록출원 및 분할출원 되었는가?,보정기간내에 보정서를 제출하였는가? 등 총 15가지 판단사항 보정서 또는 소명서로 흠결 해소 하실수 있는데 흠결해소가 되셨다면 실체심사를 하며 해소가 되지 않았다면 무효 및 반려 후 행정소송됩니다. *무효처분에 대해서는 행정법원등에 행정소송 제기 가능</figcaption>
		</figure>
		</div>
		</div>

		<div class="pop_bottom">
		<div class="btnAreaLR">
		<div class="btnA_c"><a class="btn blue2 modal-close" href="#">창닫기</a></div>
		</div>
		</div>
		</div>
		</div>
		</div>
		</li>
	</ul>
	</li>
	<li><strong>심사청구</strong>
	<ul class="list_02">
		<li>심사업무를 경감하기 위하여 모든 출원을 심사하는 대신 출원인이 심사를 청구한 출원에 대해서만 심사하는 제도 특허출원에 대하여 출원 후 3년간 심사청구를 하지 않으면 출원이 없었던 것으로 간주(실용신안등록출원의 심사청구기간은 3년)</li>
		<li>※ 방어출원 : 특허권을 얻기보다는 타인의 권리 획득을 막기 위한 출원</li>
	</ul>
	</li>
	<li><strong>출원공개</strong>
	<ul class="list_02">
		<li>출원공개제도는 출원 후 1년 6개월이 경과하면 그 기술내용을 지식재산처이 공보의 형태로 일반인에게 공개하는 제도 심사가 지연될 경우 출원기술의 공개가 늦어지는 것을 방지하기 위하여 도입</li>
		<li>※ 출원공개가 없다면, 출원기술은 설정등록 후 특허공보로서 공개됨 출원공개 후, 제3자가 공개된 기술내용을 실시하는 경우 출원인은 그 발명이 출원된 발명임을 서면으로 경고할 수 있으며, 경고일로부터 특허권 설정등록일까지의 실시에 대한 보상금을 권리획득 후 청구할 수 있음 (가보호권리)</li>
		<li>※ 1년 6월의 근거 : 우선권주장을 수반하는 외국출원과 국내출원의 균형 유지(우선기간 12월, 우선권증명서제출기간 4월, 공개준비 2월</li>
	</ul>
	</li>
	<li><strong>실체심사</strong></li>
</ul>
</div>

<ul class="list_02">
	<li data-brl-use="PH">특허요건, 즉 산업상 이용가능성, 신규성 및 진보성을 판단하는 심사</li>
	<li data-brl-use="PH">이와 함께 공개의 대가로 특허를 부여하게 되므로 일반인이 쉽게 실시할 수 있도록 기재하고 있는가를 동시에 심사(기재요건)</li>
	<li><a class="btn add2 modal-open" href="#" title="실체심사흐름도">실체심사 흐름도(클릭)</a>
	<div class="modal-wrapper" id="f02">
	<div class="modal-bg">&nbsp;</div>

	<div class="modal-content">
	<div class="pop_title">
	<h3>실체심사 흐름도</h3>
	<a class="pop_close modal-close" href="#">팝업 닫기</a></div>

	<div class="p_con">
	<div class="pop_boby">
	<div class="img-wrap">
	<figure><img alt="실체심사흐름도" src="/resource/images/patent/patent_img200903.png" />
	<figcaption>방식심사 후 발명의 내용 파악(A)합니다. 제출된 보정서가 여러개인 경우 최종 명세서 확정 명세서 기재를 바탕으로 발명의 내용 파악 복합기술의 경우는 다른 심사관과 협의 그후 선행기술조사(B)를 하며 출원발명과 기술적으로 유사한 문헌 검색(국내외 특허문헌 및 국내외 논문, 저널 등 비특허문헌) 특허성 판단(C)을 하는데 출원발명과 조사된 선행기술과 대비(신규성.진보성 유무, 선원.확대된 선원 유무 등) 기타 다른 거절이유가 있는지 추가 판단(산업상 이용가능성이 있는지 여부, 명세서 기재가 잘 되었는지 여부 등) 판단이 YES일 경우 특허결정을 하고 판단이 NO일 경우 거절이유를 통지합니다.</figcaption>
	</figure>
	</div>
	</div>

	<div class="pop_bottom">
	<div class="btnAreaLR">
	<div class="btnA_c"><a class="btn blue2 modal-close" href="#">창닫기</a></div>
	</div>
	</div>
	</div>
	</div>
	</div>
	</li>
	<li><a class="btn add2 modal-open" href="#" title="특허출원의거절이유">특허출원의 거절이유(클릭)</a>
	<div class="modal-wrapper" id="f03">
	<div class="modal-bg">&nbsp;</div>

	<div class="modal-content">
	<div class="pop_title">
	<h3>특허출원의 거절이유 (특허법제62조)</h3>
	<a class="pop_close modal-close" href="#">팝업 닫기</a></div>

	<div class="p_con">
	<div class="pop_boby">
	<table class="table_type">
		<caption>특허출원의 거절이유(특허법제62조) 표</caption>
		<thead>
			<tr>
				<th scope="col">특허법 조문</th>
				<th scope="col">판단 대상</th>
			</tr>
		</thead>
		<tbody>
			<tr>
				<td>제25조(외국인의 권리능력)</td>
				<td>외국인의 권리 향유요건 충족 여부</td>
			</tr>
			<tr>
				<td>제29조제1항본문(성립성)</td>
				<td>발명에 해당하는지 여부, 산업상 이용가능성 여부</td>
			</tr>
			<tr>
				<td>제29조제1항제1호(신규성)</td>
				<td>출원전 국내외 공지공용기술인지 여부</td>
			</tr>
			<tr>
				<td>제29조제1항제2호(신규성)</td>
				<td>출원전 간행물과 동일한지 여부</td>
			</tr>
			<tr>
				<td>제29조제2항(진보성)</td>
				<td>출원전 공지기술로부터 용이하게 발명할 수 있는지</td>
			</tr>
			<tr>
				<td>제29조제3항,제4항(확대된 선원)</td>
				<td>출원전 출원되고 출원후 공개된 타출원과의 동일성 여부</td>
			</tr>
			<tr>
				<td>제31조(식물특허발명)</td>
				<td>무성반복생식 변종식물 여부 <span class="w_red">(2006.9.30 이전 출원)</span></td>
			</tr>
			<tr>
				<td>32조(특허받을 수 없는 발명)</td>
				<td>공서양속 및 공중위생을 해하는지 여부</td>
			</tr>
			<tr>
				<td>제33조 제1항(특허받을 수 있는 자)</td>
				<td>정당권리자 인지 여부</td>
			</tr>
			<tr>
				<td>제36조(선원)</td>
				<td>두 출원간 청구범위가 동일한지 여부</td>
			</tr>
			<tr>
				<td>제42조제3항(상세한 설명 기재요건)</td>
				<td>상세한 설명의 기재불비</td>
			</tr>
			<tr>
				<td>제42조제4항(청구범위 기재요건)</td>
				<td>청구범위의 기재불비</td>
			</tr>
			<tr>
				<td>제42조제8항(청구범위 기재방법)</td>
				<td>청구범위의 형식적 기재불비</td>
			</tr>
			<tr>
				<td>제44조(공동출원)</td>
				<td>공유자 전원의 출원인지 여부</td>
			</tr>
			<tr>
				<td>제45조(1특허출원의 범위)</td>
				<td>단일성 충족 여부</td>
			</tr>
			<tr>
				<td>제47조제2항(특허출원의 보정)</td>
				<td>신규사항추가, 보정이 적법 여부</td>
			</tr>
			<tr>
				<td>제52조제1항(분할출원)</td>
				<td>분할출원 범위 <span class="w_red">(2006.10.1 이후 출원)</span></td>
			</tr>
			<tr>
				<td>제53조제1항(변경출원)</td>
				<td>변경출원 범위 <span class="w_red">(2006.10.1 이후 출원)</span></td>
			</tr>
			<tr>
				<td>조약</td>
				<td>조약의 규정에 위반된 경우</td>
			</tr>
		</tbody>
	</table>
	</div>

	<div class="pop_bottom">
	<div class="btnAreaLR">
	<div class="btnA_c"><a class="btn blue2 modal-close" href="#">창닫기</a></div>
	</div>
	</div>
	</div>
	</div>
	</div>
	</li>
	<li data-brl-use="PH">※ 최초/최후 거절이유 통지와 보정각하</li>
	<li data-brl-use="PH">심사관은 심사에 착수하여 거절이유를 발견하면 최초거절이유를 통지하고 심사 착수후 보정서가 제출되어 다시 심사한 결과 보정에 의해 발생한 거절이유를 발견하면 최후거절이유를 통지</li>
	<li data-brl-use="PH">심사관은 최후거절이유를 통지한 후 보정에 보정각하 사유를 발견하면 결정으로 보정을 각하하고 이전 명세서로 심사</li>
	<li><a class="btn add2 modal-open" href="#" title="거절이유통지후 심사흐름도">거절이유통지후 심사 흐름도(클릭)</a>
	<div class="modal-wrapper" id="f04">
	<div class="modal-bg">&nbsp;</div>

	<div class="modal-content">
	<div class="pop_title">
	<h3>거절이유 통지 후 심사 흐름도 <span>(2001.7.1 이후출원)</span></h3>
	<a class="pop_close modal-close" href="#">팝업 닫기</a></div>

	<div class="p_con">
	<div class="pop_boby">
	<div class="img-wrap">
	<figure><img alt="거절이유 통지 후 심사 흐름도" src="/resource/images/patent/patent_img200904.png" />
	<figcaption>최초거절이유 통지후 의견서 및 보정1를 제출합니다. 제출하고 거절이유가 존재하지 않다면 특허결정되고 거절이유가 존재하다면 기 통지한 거절이유가 됩니다. 기 통지한 거절이유가 맞다면 거절결정되고 보정서가 제출되어 다시심사한다. 심사한내용이 아니라면 최초거절이유 통지되고 맞다면 최후거절이유 통지됩니다. 보정요건 충족을 위해 의건서/보정 2를 제출하고 보정요건이 충족하지 않다면 보정각하후 거절이유존재여부를 묻지만 요건이 충족하다면 바로 거절이유 존재여부를 물을수 있습니다. 거절이유가 존재하지 않다면 특허결정을 하지만 거절이유가 존재하다면 거절이유를 통지하고 아니라면 다시 심사를 맞다면 거절결정됩니다.</figcaption>
	</figure>
	</div>
	</div>

	<div class="pop_bottom">
	<div class="btnAreaLR">
	<div class="btnA_c"><a class="btn blue2 modal-close" href="#">창닫기</a></div>
	</div>
	</div>
	</div>
	</div>
	</div>
	</li>
</ul>

<div data-brl-use="PH">
<ul>
	<li><strong>특허결정</strong>

	<ul class="list_02">
		<li>해당 출원이 특허요건을 충족하는 경우, 심사관이 특허를 부여하는 처분</li>
	</ul>
	</li>
	<li><strong>설정등록과 등록공고</strong>
	<ul class="list_02">
		<li>특허결정이 되면 출원인은 등록료를 납부하여 특허권을 설정등록. 이때부터 권리가 발생됨</li>
		<li>설정등록된 특허출원 내용을 등록공고로 발행하여 일반인에게 공표함</li>
	</ul>
	</li>
	<li><strong>거절결정</strong>
	<ul class="list_02">
		<li>출원인이 제출한 의견서 및 보정서에 의하여도 거절이유가 해소되지 않은 경우 특허를 부여하지 않는 처분</li>
	</ul>
	</li>
	<li><strong>거절결정불복심판</strong>
	<ul class="list_02">
		<li>거절결정을 받은 자가 특허심판원에 거절결정이 잘못되었음을 주장하면서 그 거절결정의 취소를 요구하는 심판절차</li>
	</ul>
	</li>
	<li><strong>무효심판</strong>
	<ul class="list_02">
		<li>심사관 또는 이해관계인(다만, 특허권의 설정등록이 있는 날부터 등록공고일 후 3월 이내에는 누구든지)이 특허에 대하여 무효사유(특허요건, 기재불비, 모인출원 등)가 있음을 이유로 그 특허권을 무효시켜 줄 것을 요구하는 심판절차</li>
		<li>※ 무효심결이 확정되면 그 특허권은 처음부터 없었던 것으로 간주</li>
	</ul>
	</li>
</ul>
</div>

<h4 data-brl-use="PH">특허심사 주요제도 안내</h4>

<ul class="list_01" data-brl-use="PH">
	<li><strong>우선심사제도</strong>

	<ul class="list_02">
		<li>특허출원은 심사청구 순서에 따라 심사하는 것이 원칙이나, 모든 출원에 대해서 예외없이 이러한 원칙을 적용하다 보면 공익이나 출원인의 권리를 적절하게 보호할 수 없는 면이 있어 일정한 요건을 만족하는 출원에 대해서는 심사청구 순위에 관계없이 다른 출원보다 먼저 심사하는 제도</li>
		<li><a class="btn add2" href="/ko/kpoContentView.do?menuCd=SCD0200225" title="우선심사제도 상세 안내로 이동됩니다">우선심사 제도 상세 안내(클릭)</a></li>
		<li><a class="btn add2 modal-open" href="#" title="우선심사흐름도">우선심사 흐름도(클릭)</a>
		<div class="modal-wrapper" id="f05">
		<div class="modal-bg">&nbsp;</div>

		<div class="modal-content">
		<div class="pop_title">
		<h3>우선심사 흐름도</h3>
		<a class="pop_close modal-close" href="#">팝업 닫기</a></div>

		<div class="p_con">
		<div class="pop_boby">
		<div class="img-wrap">
		<figure><img alt="우선심사흐름도" src="/resource/images/patent/patent_img200905.png" />
		<figcaption>우선심사신청후 방식하자가 맞다면 보정명령/반려이유통지하고 방식하자 치유를 묻습니다 아니라면 무효/반려처분하고 맞다면 우선심사대상 적합을 묻습니다. 반면 방식하자가 아니라면 우선심사대상적합을 묻습니다. 적합 하다면 우선심사결정통지후 우선심사를 하고 적합하지 않다면 보완지시후 우선심사대상적합여부 재심사를 묻습니다. 재심사를 안한다면 우선심사신청이 각하되고 재심사를 한다면 우섬심사결정통지후 우선심사 하게 됩니다.</figcaption>
		</figure>
		</div>
		</div>

		<div class="pop_bottom">
		<div class="btnAreaLR">
		<div class="btnA_c"><a class="btn blue2 modal-close" href="#">창닫기</a></div>
		</div>
		</div>
		</div>
		</div>
		</div>
		</li>
	</ul>
	</li>
	<li><strong>청구범위제출 유예제도</strong>
	<ul class="list_02">
		<li>출원일부터 1년 2개월이 되는 날까지(출원심사청구의 취지를 통지받은 경우에는 통지받은 날부터 3개월이 되는 날까지) 명세서의 청구범위 제출을 유예할 수 있는 제도</li>
		<li>※ 제출기한 이내에 청구범위를 제출하지 않으면 취하 간주되며, 청구범위가 제출된 경우에 한하여 심사청구 가능</li>
	</ul>
	</li>
	<li><strong>심사유예신청제도</strong>
	<ul class="list_02">
		<li>늦은 심사를 바라는 고객의 요구를 충족시키기 위해 특허출원인이 원하는 유예시점에 특허출원에 대한 심사를 받을 수 있는 제도</li>
		<li>늦게 심사받는 대신 희망시점에 맞춰 심사서비스 제공(심사유예 희망시점으로부터 3월 이내 심사서비스 제공 예정</li>
		<li>심사청구시 또는 심사청구일로부터 9개월 이내에 유예희망시점을 기재한 심사유예신청서를 제출하면 이용 가능(별도 신청료 없음)</li>
	</ul>
	</li>
	<li><strong>분할출원</strong>
	<ul class="list_02">
		<li>2이상의 발명을 하나의 특허출원으로 신청한 경우 그 일부를 하나 이상의 출원으로 분할하여 출원</li>
		<li><a class="btn add2 modal-open" href="#" title="분할출원흐름도">분할출원 흐름도(클릭)</a>
		<div class="modal-wrapper" id="f06">
		<div class="modal-bg">&nbsp;</div>

		<div class="modal-content">
		<div class="pop_title">
		<h3>분할출원 흐름도</h3>
		<a class="pop_close modal-close" href="#">팝업 닫기</a></div>

		<div class="p_con">
		<div class="pop_boby">
		<div class="img-wrap">
		<figure><img alt="분할출원 흐름도" src="/resource/images/patent/patent_img200906.png?v=2024050101" />
		<figcaption>분할에는 출원과와 심사관이 분할되어 이어져 있습니다. 원출원후 분할출원 그리고 방식흠결을 물어보고 흠결이 맞다면 소명기회/보정명령후 방식흠결치유를 묻고 아니라면 반려/무효처분을 맞다면 분할출원실체요건구비를 묻겠지만 방식흠결이 아니라면 바로 분할출원실체요건구비를 묻습니다 실체요건구비가 맞다면 분할출원 인정후 심사하며 아니라면 원출원 &#39;06.10.1.이후가 맞다면 거절이유통지하며 아니라면 의견서/보정서를 제출후 분할불인정이유 치유합니다. 치유가 되었다면 분할출원 인정 후 심사를 하고 치유가 되지 않았다면 분할출원 불인정통지후 출원일 불소급 후 심사를 합니다.</figcaption>
		</figure>
		</div>
		</div>

		<div class="pop_bottom">
		<div class="btnAreaLR">
		<div class="btnA_c"><a class="btn blue2 modal-close" href="#">창닫기</a></div>
		</div>
		</div>
		</div>
		</div>
		</div>
		</li>
	</ul>
	</li>
	<li><strong>변경출원</strong>
	<ul class="list_02">
		<li>출원인은 출원후 설정등록 또는 거절결정 확정 전까지 특허에서 실용신안 또는 실용신안에서 특허로 변경하여 자신에게 유리한 출원을 선택할 수 있음</li>
		<li><a class="btn add2 modal-open" href="#" title="변경출원흐름도">변경출원 흐름도(클릭)</a>
		<div class="modal-wrapper" id="f07">
		<div class="modal-bg">&nbsp;</div>

		<div class="modal-content">
		<div class="pop_title">
		<h3>변경출원 흐름도</h3>
		<a class="pop_close modal-close" href="#">팝업 닫기</a></div>

		<div class="p_con">
		<div class="pop_boby">
		<div class="img-wrap">
		<figure><img alt="변경출원 흐름도" src="/resource/images/patent/patent_img200907.png" />
		<figcaption>출원과와 심사관으로 변경출원이 되어 있습니다. 원출원후 변경출원 그리고 방식흠결을 묻습니다 흠결이 맞다면 소명기회/보정명령 후 방식흠결 치유를 합니다 아니면 반려/무효처분을 맞다면 변경출원실체요건구비를 묻습니다. 반면 방식흠결여부가 아니라면 변경출원실체요건구비를 묻습니다. 요건구비가 아니라면 변경출원 인정후 심사를 하고 맞다면 거절이유를 통지합니다.</figcaption>
		</figure>
		</div>
		</div>

		<div class="pop_bottom">
		<div class="btnAreaLR">
		<div class="btnA_c"><a class="btn blue2 modal-close" href="#">창닫기</a></div>
		</div>
		</div>
		</div>
		</div>
		</div>
		</li>
	</ul>
	</li>
	<li><strong>조약우선권주장</strong>
	<ul class="list_02">
		<li>파리협약이나 WTO 회원국간 상호 인정되는 제도로 제1국출원후 1년내에 다른 가입국에 출원하는 경우 제1국출원에 기재된 발명에 대하여 신규성 진보성 등 특허요건 판단일을 소급하여 주는 제도</li>
		<li><a class="btn add2 modal-open" href="#" title="조약우선권주장 흐름도">조약우선권주장 흐름도(클릭)</a>
		<div class="modal-wrapper" id="f08">
		<div class="modal-bg">&nbsp;</div>

		<div class="modal-content">
		<div class="pop_title">
		<h3>조약우선권주장 흐름도</h3>
		<a class="pop_close modal-close" href="#">팝업 닫기</a></div>

		<div class="p_con">
		<div class="pop_boby">
		<div class="img-wrap">
		<figure><img alt="조약우선권주장흐름도" src="/resource/images/patent/patent_img200908.png" />
		<figcaption>우선권주장후 우선권 주장 방식흠결에 대한 판단여부를 가집니다. 방식이 맞다면 보정명령 후 흠결 치유 여부를 묻는데 아니라면 우선권주장절차 무효처분후 제2국 출원일을 기준으로 심사를 합니다. 여부가 맞다면 제1,2국 출원일 사이에 선행기술 유무를 묻습니다. 반면 우선권주장 방식흠결이 아니라면 제1,2국 출원일 사이에 선행기술 유무를 판단합니다. 판단결과가 아니라면 제1국 출원일를 기준으로 심사하며 판단이 맞다면 제2국출원발명의 제1국출원내 기재를 묻습니다. 아니라면 제2국 출원일을 기준으로 심사를 맞다면 제1국 출원일을 기준으로 심사합니다.</figcaption>
		</figure>
		</div>
		</div>

		<div class="pop_bottom">
		<div class="btnAreaLR">
		<div class="btnA_c"><a class="btn blue2 modal-close" href="#">창닫기</a></div>
		</div>
		</div>
		</div>
		</div>
		</div>
		</li>
	</ul>
	</li>
	<li><strong>국내우선권주장</strong>
	<ul class="list_02">
		<li>선출원후 1년 이내에 선출원 발명을 개량한 발명을 한 경우 하나의 출원에 선출원 발명을 포함하여 출원할 수 있도록 하는 제도</li>
		<li><a class="btn add2 modal-open" href="#" title="국내우선권주장 흐름도">국내우선권주장 흐름도(클릭)</a>
		<div class="modal-wrapper" id="f09">
		<div class="modal-bg">&nbsp;</div>

		<div class="modal-content">
		<div class="pop_title">
		<h3>국내우선권주장 흐름도</h3>
		<a class="pop_close modal-close" href="#">팝업 닫기</a></div>

		<div class="p_con">
		<div class="pop_boby">
		<div class="img-wrap">
		<figure><img alt="국내우선권주장흐름도" src="/resource/images/patent/patent_img200909.png" />
		<figcaption>우선권주장후 우선권 주장 방식흠결을 판단합니다. 판단이 맞다면 보정명령후 방식 흠결 치유여부를 묻는데 아니라면 우선권 주장절차 무효처분을하고 맞다면 선출원과 후출원의 출원일 사이에 선행기술 유무 여부를 판단합니다. 반면 우선권주장 방식흠결판단이 아니라면 선출원과 후출원의 출원일 사이에 선행기술 유무 여부를 판단합니다. 판단결과 아니라면 선출원의 출원일을 기준으로 심사하고 판단결과가 맞다면 후출원 발명의 선출원 기재여부를 묻습니다. 기재여부가 맞다면 선출원 출원일을 기준으로 심사하고 아니라면 후출원의 출원일을 기준으로 심사 합니다.</figcaption>
		</figure>
		</div>
		</div>

		<div class="pop_bottom">
		<div class="btnAreaLR">
		<div class="btnA_c"><a class="btn blue2 modal-close" href="#">창닫기</a></div>
		</div>
		</div>
		</div>
		</div>
		</div>
		</li>
	</ul>
	</li>
	<li><strong>직권보정제도</strong>
	<ul class="list_02">
		<li>출원에 대해 심사한 결과 특허결정이 가능하나 명백한 오탈자, 참조부호의 불일치 등과 같은 사소한 기재불비만 존재하는 경우, 의견제출통지를 하지 않고도 보다 간편한 방법으로 명세서의 단순한 기재불비 사항을 수정할 수 있도록 함으로써 심사 지연을 방지하고 등록 명세서에 완벽을 기하고자 마련된 제도</li>
		<li>(2009.7.1이후 등록결정부터)</li>
	</ul>
	</li>
	<li><strong>재심사청구(심사전치) 제도</strong>
	<ul class="list_02">
		<li>심사후 거절결정된 경우 거절결정불복심판을 청구한 후 명세서를 보정한 건에 대해 다시 심사를 하였으나(심사전치제도) 개정 특허법에 따라 거절결정후 심판청구를 하지 않더라도 보정과 동시에 재심사를 청구하면 심사관에게 다시 심사받을 수 있음(재심사청구제도)</li>
		<li><a class="btn add2 modal-open" href="#" title="재심사청구 흐름도">재심사청구 흐름도 [2009.7.1이후 출원] (클릭)</a>
		<div class="modal-wrapper" id="f10">
		<div class="modal-bg">&nbsp;</div>

		<div class="modal-content">
		<div class="pop_title">
		<h3>재심사청구 흐름도 <span>(2009.7.1 이후 출원)</span></h3>
		<a class="pop_close modal-close" href="#">팝업 닫기</a></div>

		<div class="p_con">
		<div class="pop_boby">
		<div class="img-wrap">
		<figure><img alt="재심사청구 흐름도(2009.7.1 이후 출원)" src="/resource/images/patent/patent_img200910.png" />
		<figcaption>보정 및 재심사청구(의견서)제출후 방식심사를 가지게 됩니다. 심사후 보정적합을 묻는데 그전에 거절결정취하간주를 묻습니다. 보정 적합이 아니라면 보정각하 후 거절이유를 판단하고 보정적합이 맞다면 바로 거절이유를 판단합니다. 거절이유가 아니라면 바로 특허결정을 하실수 있지만 거절이유가 있다면 거절이유 판단하는데 판단에는 다음과 같이 3가지로 나뉘어 진다. 1은 최초 거절이유통지전부터 있었으나 지적하지 않은 거절이유, 2는 거절이유통지후 보정에 의하여 발생한 지적하지 않은 거절이유,3은 이전의 거절이유통지에 지적한 거절이유 거절이유 판단이 1이면 최초거절이유 통지후 의견서 및 보정을 제출 심사하여 거절이유를 다시 묻고 거절이유판단을 다시 하며 1번일 결우 최초거절이유통지로 다시 돌아가며 3번일경우 재거절결정하고 2번일 경우 최후거절이유를 통지 후 의견서 및 보정을 다시하며 보정 적합여부 후 아니면 보정각하를 맞다면 거절이유를 묻고 아니면 특허결정은 맞다면 거절이유를 또 다시 묻습니다. 거절이유 판단이 2면 최후거절이유통지후 의견서 및 보정을 제출 심사하여 보정적합 여부를 묻고 아니면 보정각하루 거절이유를 따지며 맞으면 그냥 거절이유를 묻습니다. 거절이유가 아니면 특허결정하고 맞다면 거절이유 판단하여 다시 진행합니다. 거절이유 판단이 3이면 재거절결정이 됩니다.</figcaption>
		</figure>
		</div>
		</div>

		<div class="pop_bottom">
		<div class="btnAreaLR">
		<div class="btnA_c"><a class="btn blue2 modal-close" href="#">창닫기</a></div>
		</div>
		</div>
		</div>
		</div>
		</div>
		</li>
		<li><a class="btn add2 modal-open" href="#" title="심사전치 흐름도">심사전치 흐름도 [2001.7.1이후, 2009.6.30 이전 출원] (클릭)</a>
		<div class="modal-wrapper" id="f11">
		<div class="modal-bg">&nbsp;</div>

		<div class="modal-content">
		<div class="pop_title">
		<h3>심사전치 흐름도 <span>(2001.7.1이후, 2009.6.30 이전 출원)</span></h3>
		<a class="pop_close modal-close" href="#">팝업 닫기</a></div>

		<div class="p_con">
		<div class="pop_boby">
		<div class="img-wrap">
		<figure><img alt="심사전치 흐름도(2001.7.1 이후 2001.6.30 이전 출원)" src="/resource/images/patent/patent_img200911.png" />
		<figcaption>심판 청구 후 의견서 및 보정1을 제출후 방식심사를 가지게 됩니다. 심사후 보정적합을 묻는데 그전에 거절결정취하간주를 묻습니다. 보정 적합이 아니라면 보정각하 후 거절이유를 판단하고 보정적합이 맞다면 바로 거절이유를 판단합니다. 거절이유가 아니라면 바로 특허결정을 하실수 있지만 거절이유가 있다면 거절이유 판단하는데 판단에는 다음과 같이 3가지로 나뉘어 진다. 1은 최초 거절이유통지전부터 있었으나 지적하지 않은 거절이유, 2는 거절이유통지후 보정에 의하여 발생한 지적하지 않은 거절이유,3은 이전의 거절이유통지에 지적한 거절이유 거절이유 판단이 1이면 최초거절이유 통지후 의견서 및 보정2을 제출 심사하여 거절이유를 다시 묻고 거절이유판단을 다시 하며 1번일 결우 최초거절이유통지로 다시 돌아가며 3번일경우 원결정유지하고 2번일 경우 최후거절이유를 통지 후 의견서 및 보정3을 다시하며 보정 적합여부 후 아니면 보정각하를 맞다면 거절이유를 묻고 아니면 특허결정은 맞다면 거절이유를 또 다시 묻습니다. 거절이유 판단이 2면 최후거절이유통지후 의견서 및 보정을 제출 심사하여 보정적합 여부를 묻고 아니면 보정각하루 거절이유를 따지며 맞으면 그냥 거절이유를 묻습니다. 거절이유가 아니면 특허결정하고 맞다면 거절이유 판단하여 다시 진행합니다. 거절이유 판단이 3이면 원결정유지 됩니다.</figcaption>
		</figure>
		</div>
		</div>

		<div class="pop_bottom">
		<div class="btnAreaLR">
		<div class="btnA_c"><a class="btn blue2 modal-close" href="#">창닫기</a></div>
		</div>
		</div>
		</div>
		</div>
		</div>
		</li>
	</ul>
	</li>
</ul>

<h4 data-brl-use="PH">처리기간</h4>

<ul class="list_01" data-brl-use="PH">
	<li>심사처리기간이란 심사청구일로부터 심사착수 시점까지의 기간으로 심사처리기간의 장기화는 권리행사기간의 단축을 초래하고, 신기술의 사업화와 수익화를 저해함</li>
	<li>이에 따라 지식재산처는&nbsp;특허심사관 증원, 선행기술조사 외주용역 확대, 자동검색시스템 구축 등을 통해 주요국 수준인 10~11개월대의 안정적인 특허심사처리기간을 유지 중</li>
</ul>

<h3 data-brl-use="PH">국제특허분류</h3>

<h4 data-brl-use="PH">국제특허분류의 성립배경</h4>

<p class="ct2">미국(USPC), 일본(JPC), 유럽(ECLA) 등 각국마다 다른 분류체계를 사용하여 왔으나, 국제적으로 통일된 특허 분류체계가 필요함에 따라 1968년에 국제특허분류(IPC)가 도입됨</p>

<h4 data-brl-use="PH">국제특허분류의 목적</h4>

<ul class="list_01" data-brl-use="PH">
	<li>특허문헌을 체계적으로 정리해서, 특허문헌에 포함되어 있는 기술 및 권리정보에 용이하게 접근할 수 있게 하기 위함</li>
	<li>특허정보의 모든 이용자에게 정보를 선택적으로 보급하기 위함</li>
	<li>주어진 기술분야에서 공지기술을 조사하기 위함</li>
	<li>여러 영역에서의 기술발전을 평가하는 공업소유권 통계를 내기 위함</li>
</ul>

<h4 data-brl-use="PH">국제특허분류의 개정연혁</h4>

<ul class="list_01" data-brl-use="PH">
	<li>IPC 제1판 : 1968년 9월 1일 ~ 1974년 6월 30일</li>
	<li>IPC 제2판 : 1974년 7월 1일 ~ 1979년 12월 31일</li>
	<li>IPC 제3판 : 1980년 1월 1일 ~ 1984년 12월 31일</li>
	<li>IPC 제4판 : 1985년 1월 1일 ~ 1989년 12월 31일</li>
	<li>IPC 제5판 : 1990년 1월 1일 ~ 1994년 12월 31일</li>
	<li>IPC 제6판 : 1995년 1월 1일 ~ 1999년 12월 31일</li>
	<li>IPC 제7판 : 2000년 1월 1일 ~ 2005년 12월 31일</li>
	<li>IPC 제8판 : 2006년 1월 1일 ~ 2008년 12월 31일</li>
	<li>Version 2007.01 : 2007년 1월 1일 ~ 2007년 9월 30일</li>
	<li>Version 2007.10 : 2007년 10월 1일 ~ 2007년 12월 31일</li>
	<li>Version 2008.01 : 2008년 1월 1일 ~ 2008년 3월 31일</li>
	<li>Version 2008.04 : 2008년 4월 1일 ~ 2008년 12월 31일</li>
	<li>Version 2009.01 : 2009년 1월 1일 ~ 2009년 12월 31일</li>
	<li>Version 2010.01 : 2010년 1월 1일 ~ 2010년 12월 31일</li>
	<li>Version 2011.01 : 2011년 1월 1일 ~ 2011년 12월 31일</li>
	<li>Version 2012.01 : 2012년 1월 1일 ~ 2012년 12월 31일</li>
	<li>Version 2013.01 : 2013년 1월 1일 ~ 2013년 12월 31일</li>
	<li>Version 2014.01 : 2014년 1월 1일 ~ 2014년 12월 31일</li>
	<li>Version 2015.01 : 2015년 1월 1일 ~ 2015년 12월 31일</li>
	<li>Version 2016.01 : 2016년 1월 1일 ~ 2016년 12월 31일</li>
	<li>Version 2017.01 : 2017년 1월 1일 ~ 2017년 12월 31일</li>
	<li>Version 2018.01 : 2018년 1월 1일 ~ 2018년 12월 31일</li>
	<li>Version 2019.01 : 2019년 1월 1일 ~ 2019년 12월 31일</li>
	<li>Version 2020.01 : 2020년 1월 1일 ~ 2020년 12월 31일</li>
</ul>

<h4 data-brl-use="PH">국제특허분류의 구조</h4>

<ul class="list_01">
	<li>섹션, 클래스, 서브클래스 및 메인그룹 또는 서브그룹의 계층구조로 이루어짐
	<p class="ct3">예) F16K 1/00(or 1/02)의 경우</p>

	<table class="table_type mt10 mb10" data-brl-tbltype="1" data-brl-use="TH">
		<caption><strong>국제특허분류의 구조 표</strong>

		<p>국제특허분류의 구조 정보를 나타내는 표이며, 분류기호, F, -, 16, K, 1/100, 1/20 로 구성되어있습니다.</p>
		</caption>
		<thead>
			<tr>
				<th scope="col">분류기호</th>
				<th scope="col">F</th>
				<th scope="col">-</th>
				<th scope="col">16</th>
				<th scope="col">K</th>
				<th scope="col">1/100</th>
				<th scope="col">1/20</th>
			</tr>
		</thead>
		<tbody>
			<tr>
				<td>구분</td>
				<td>섹션</td>
				<td>서브섹션</td>
				<td>클래스</td>
				<td>서브클래스</td>
				<td>메인그룹</td>
				<td>서브그룹</td>
			</tr>
			<tr>
				<td>분류타이틀</td>
				<td>기계공학</td>
				<td>공업일반</td>
				<td>기계요소</td>
				<td>밸브</td>
				<td>리프트밸브</td>
				<td>나사스핀들</td>
			</tr>
		</tbody>
	</table>
	</li>
	<li data-brl-use="PH">섹션, 클래스, 서브클래스 및 메인그룹 또는 서브그룹의 계층구조로 이루어짐
	<ul class="list_02">
		<li>A 섹션 - 생활필수품</li>
		<li>B 섹션 - 처리조작, 운수</li>
		<li>C 섹션 - 화학, 야금</li>
		<li>D 섹션 - 섬유, 종이</li>
		<li>E 섹션 - 고정구조물</li>
		<li>F 섹션 - 기계공학, 조명, 가열, 무기, 폭파</li>
		<li>G 섹션 - 물리학</li>
		<li>H 섹션 - 전기</li>
	</ul>
	</li>
	<li data-brl-use="PH">세부내용은 지식재산처 홈페이지 메인화면의 &#39;분류코드 조회&#39; 또는 MOIP&nbsp;홈페이지 <a href="http://www.wipo.int/classifications/ipc/en/" target="_blank" title="WIPO 홈페이지(새창) 바로가기">(www.wipo.int/classifications/ipc/en/)</a> 참조</li>
</ul>

<div data-brl-use="PH">
<h3>선진특허분류</h3>

<h4>선진특허분류(CPC) 소개</h4>

<ul class="list_01">
	<li>CPC는 국제특허분류(IPC)보다 세분화된 특허분류체계입니다. 효율적인 선행기술조사를 위해 미국, 유럽 지식재산처 주도로 2012년 개발되었고, 우리나라는 2015년 1월 이후 신규출원에 IPC와 CPC를 함께 부여하고 있습니다.</li>
	<li>세부내용은 지식재산처 홈페이지 메인화면의 &lsquo;분류코드 조회&rsquo; 또는 CPC 홈페이지 <a href="http://www.cooperativepatentclassification.org/" target="_blank" title="CPC 홈페이지(새창) 바로가기">www.cooperativepatentclassification.org</a> 참조</li>
</ul>

<h3>국제기구 및 국제조약</h3>

<h4>세계지식재산기구(WIPO, World Intellectual Property Organization)</h4>

<ul class="list_01">
	<li>산업재산권 문제를 위한 파리협약(1883), 저작권 문제를 위한 베른조약(1886), 특허협력조약 및 특허법조약 등을 관리 하고 지식재산권 분야의 국제협력을 위하여 1967년 스톡홀름에서 체결하고 1970년에 발효한 세계 지식재산기구설립조약에 따라 설립됨 &rarr; &#39;74년 국제연합의 전문기구가 됨</li>
	<li><strong>회원국 :</strong> 184개국 (한국은 &#39;79년 3월에 가입)</li>
	<li><strong>WIPO의 주요 임무</strong>
	<ul class="list_02">
		<li>지적재산권의 효율적 보호를 촉진</li>
		<li>지식재산권 관련 조약의 체결, 운용 및 각국 법제의 조화 도모</li>
		<li>개발도상국에 대한 법제,기술측면의 원조 실시</li>
	</ul>
	</li>
	<li><strong>WIPO 구성</strong>
	<p class="ct1">일반총회, 체약국회의, 조정위원회, 국제사무국 4개 기구</p>
	</li>
</ul>

<h4>파리협약(Paris Convention)</h4>

<ul class="list_01">
	<li>산업재산권의 국제적 보호를 위하여 1883년 파리에서 체결
	<ul class="list_02">
		<li>각국의 특허제도상의 차이를 인정하면서 중요한 사항에 대하여 국제적으로 통일된 규범을 규정</li>
		<li>※ 우리나라는 &#39;80년 5월에 가입, 가맹국은 172개국</li>
	</ul>
	</li>
	<li><strong>주요내용</strong>
	<ul class="list_02">
		<li>- 특허독립의 원칙 (속지주의)</li>
		<li>동일한 발명에 대하여 복수의 동맹국에서 특허를 부여받았다 하더라도 그 특허는 각각 독립적으로 존속,소멸 (회원국의 Sovereignty 인정)</li>
		<li>- 내외국인 동등의 원칙</li>
		<li>동맹국의 국민을 자국민 수준으로 대우 (각국은 자국산업의 보호를 위하여 외국인에 대해서는 특허를 부여하지 않으려는 경향이 있음)</li>
		<li>- 우선권제도</li>
		<li>원국에 출원(선출원)한 자가 동일한 발명을 1년 이내에 타 회원국에 우선권을 주장하면서 출원(후출원)하는 경우후출원의 특허요건을 판단함에 있어서, 선출원의 출원일에 출원된 것으로 취급하는 제도 &rarr; 외국에 출원하는 경우, 거리,언어,절차상의 제약으로부터 발생할 수 있는 출원인의 불이익을 해소</li>
	</ul>
	</li>
</ul>

<h4>특허협력조약(PCT: Patent Cooperation Treaty)</h4>

<ul class="list_01">
	<li><strong>파리조약 제19조에 따른 특별협정의 하나로서 국제적인 특허출원 절차요건의 통일화에 주안점을 두고 1970년 워싱턴에서 개최된 외교회의에서 채택되어 1978년 1월 24일 발효됨</strong></li>
	<li><strong>PCT에 의한 국제출원은 출원인이 국제사무국 또는 자국 지식재산처(수리관청)에 특허를 받고자 하는 국가를 지정하여 PCT 국제출원서를 제출하면 각 지정국에서 정규의 국내출원으로 인정해주는 제도임</strong></li>
	<li>자세한 사항은 특허마당 &rarr; PCT 참고</li>
</ul>

<h4>특허법조약(PLT : Patent Law Treaty) 및 특허실체법조약(SPLT : Substantive Patent Law Treaty)</h4>

<ul class="list_01">
	<li><strong>특허법 통일화의 논의</strong>

	<p class="ct1">각국 특허제도의 절차적 및 실체적 사항을 통일함으로써 다른 나라에서의 특허취득을 원하는 출원인의 편의성을 제고하고 비용절감을 도모하기 위한 국제적인 논의</p>
	</li>
	<li><strong>논의경과</strong>
	<p class="ct1">86년 이후 90년까지 8차에 걸친 회의 개최를 통하여 조약 기본안 (Draft Patent Harmonization Treaty)이 마련되었으나, 클린턴정부 출범 이후 미국이 선발명주의 고수입장으로 회귀함에 따라 조약 타결에 실패</p>
	</li>
	<li><strong>주의 고수입장으로 회귀함에 따라 조약 타결에 실패</strong>
	<ul class="list_02">
		<li>&#39;95년 이후 WIPO의 주도로 통일화에 장애가 되는 실체적 사항을 제외하고 논의를 진행한 결과, 2000. 6월 절차적 사항에 관한 조약인 특허법조약이 타결됨</li>
		<li>※ 10개국이 가입하면 조약발효 (2005. 7. 28. 발효), 2012. 5. 현재 32개국 가입</li>
		<li>특허법조약의 주요내용</li>
		<li>출원일 설정 기준</li>
		<li>출원서류의 서식 및 작성방법</li>
		<li>제출서류의 서식, 언어 및 표기사항</li>
		<li>기간의 연장 및 권리의 복원</li>
		<li>우선권 주장의 정정 및 추가 등</li>
	</ul>
	</li>
	<li><strong>2000년 11월 이후 WIPO</strong>는 특허요건 판단기준 등 실체적 사항을 통일하기 위하여 특허실체법조약안을 마련하고 특허법상설위원회 (Standing Committee on the Law of Patents : SCP)를 중심으로 조약안을 논의
	<ul class="list_02">
		<li>특허실체법조약안의 주요내용</li>
		<li>명세서의 내용 및 순서</li>
		<li>선행기술</li>
		<li>특허요건(특허대상, 신규성, 진보성)</li>
		<li>보정 및 정정 등</li>
	</ul>
	</li>
	<li><strong>특허실체법조약의 타결 전망</strong>
	<p class="ct1">WIPO는 그간의 SPLT 논의과정에서 각국이 제기한 의견을 종합하여 수정조약안을 작성하였으나, 전통지식 및 유전자원 문제가 새로운 변수로 부각되고 있어 단기간 내의 타결 전망은 불투명</p>
	</li>
</ul>

<h3>PCT국제출원 &rarr; 자세한 사항은 특허마당 PCT 참고</h3>

<h4>PCT 국제출원의 개요</h4>

<p class="ct2">특허협력조약(Patent Cooperation Treaty; PCT)에 의한 국제출원은 출원인이 자국 지식재산처(수리관청)에 특허를 받고자 하는 국가를 지정하여 PCT 국제출원서를 제출하면 각 지정국에서 정규의 국내출원으로 인정해 주는 제도로서, 2008.10.1 현재 139개국이 가입되어 있습니다.</p>

<h4>PCT 국제출원의 절차</h4>

<ul class="list_01">
	<li>국제출원이 접수되면 수리관청에서 서류작성의 적정여부 등에 대한 방식심사(접수 후 1월 이내, 우선일 부터 13월경)를 합니다.</li>
	<li>국제조사기관에서 선행기술조사 및 특허성에 관한 검토를 하여 그 결과를 &quot;국제조사보고서&quot; 및 &quot;견해서&quot;로 작성(조사용사본의 수령통지일부터 3월 또는 우선일 부터 9월 중 늦은 때까지이며, 통상 우선일 부터 16월경)하여 출원인 및 국제사무국에 통보합니다.</li>
	<li>국제사무국에서는 우 선일 부터 18월경과 후 국제출원 일체 및 국제조사보고서에 대하여 국제공개를 합니다.</li>
	<li>별도의 선택적 절차인 국제예비심사를 청구하는 경우(통상 우선일 부터 22월) 국제예비심사기관은 특허성에 관한 예비적인 심사를 하여 그 결과를 &quot;특허성에 관한 국제예비보고서(PCT 제2장)&quot;으로 작성하여 출원인에게 통보합니다(통상 우선일 부터 28개월 시점)</li>
	<li>출원인은 상기 보고서 등을 기초로 실제 특허를 얻고자 하는 국가에 국제출원의 번역문 및 국내수수료 등을 납부하는 국내단계에 진입(통상 우선일 부터 30개월 이내)하여 해당 지정국에서 특허 심사절차를 밟게 됩니다. 우리나라는 우선일로부터 31개월 이내에 국내 단계절차를 밟아야 합니다.</li>
	<li>※ 우리나라지식재산처&nbsp;수리관청으로 하여 출원하는 출원인은 국제조사기관으로 한국,오스트리아,호주,일본 지식재산처(일본어 출원에 한함)중 하나를 선택할 수 있으며, 국제예비심사기관으로는 한국,오스트리아,일본 지식재산처(일본에서 국제조사를 받은 경우에 한함) 중 하나를 선택할 수 있습니다.</li>
	<li>※ 국외 PCT국제출원 중 우리나라를 국제조사기관으로 지정한 나라는 필리핀, 베트남, 인도네시아, 몽고, 뉴질랜드, 미국, 싱가포르, 말레이시아, 스리랑카, 호주, 칠레, 페루, 태국이 있습니다.</li>
</ul>

<h4>PCT 국제출원에 필요한 서류</h4>

<ul class="list_01">
	<li>PCT 국제출원을 하기 위해서는 Request(국제출원서), 명세서, 청구범위, 요약서, 도면(있는 경우), 서열목록(해당하는 경우)으로 이루어진 국제출원 관련 서류를 별도로 제출해야 합니다. 국내출원시 제출한 서류를 그대로 제출하는 것이 아님에 유의하여야 합니다.</li>
	<li>명세서도 국내출원과 달리 PCT규칙에서 규정하는 기술순서에 따라 작성하여야 하며, 국내 출원과 달리 명세서와 청구범위를 구분하여 별도로 작성하여야 합니다. 국제출원서(Request)는 반드시 한국어, 영어 또는 일본어(일본어 출원의 경우)로 작성하여야 합니다.</li>
</ul>
</div>

<div class="cimg"><img alt="선출원을 기준으로 12일 경 국제출원, 16일 전 국제조사 및 견해서, 16일 경 우선권주장 정정 및 추가, 18일 전 우선권서류 조약19조 보정서제출, 18일경 국제공개, 22일경 국제예비심사청구, 28일경 조약 제34조 보정서제출, 국제예비심사보고서, 30일경 각국 국내 단계로 진행됩니다." src="/resource/images/patent/right_02.png" /></div>
<a class="btn line cbtn" href="/resource/images/patent/right_02.png" target="_blank" title="PCT 국제출원의 절차 큰 이미지로 보기(새창)">큰 이미지로 보기</a></div>

          	<!-- 내용 : e -->
          
					<!-- 만족도조사 : s -->
					





<script>

function setSatisfaction(){
	var f = document.gSatisForm;
	var i = 0;
	var status = false;
	var rbPoint = $("input:radio[name='rbSatisfaction']:checked").val();
	var opinion = $('#commentText').val().trim();
	
	for (i=0 ; i<f.rbSatisfaction.length ; i++) {
		if (f.rbSatisfaction[i].checked) {
			status = true;
			break;
		}
	}
	if (!status) {
		alert('만족도를 선택하지 않으셨습니다.');
		return false;
	}
// 2023.06.12 불만족, 매우불만족일 경우 의견 필수로 입력 LYS 	
	if ((rbPoint == 2 || rbPoint == 1) && ($('#commentText').val().trim() == "")) {
		alert('불만족에 대한 의견 부탁드립니다.');
		$("#commentText").focus();
		return false;
	}
	
	$.ajax({
		type:"post",
        contentType:"application/x-www-form-urlencoded; charset=UTF-8",
        url:"/ko/insertStdgrExmnt.do",
        data:{
        	menuCd:'SCD0200111',
        	sysCd:'SCD02',
        	rbSatisfaction:$("input:radio[name='rbSatisfaction']:checked").val(),
        	commentText:$("#commentText").val(),
        	bultnId:'',
        	ntatcSeq:''
        	},
        	dataType:'json',
        	success:function(data){
        	if(data.success == "yes"){
        		
        		var menuCd = f.sMenuCd.value;
        		var sysCd = f.sSysCd.value;
        		var ntatcSeq = f.sNtatcSeq.value;
        		var cookName = sysCd+'|'+menuCd;
        		var cookValue = f.rbSatisfaction[i].value;
        		setCookie(cookName, cookValue, 1);
        		
        		alert("코너 만족도 참여가 정상 처리되었습니다.");
        		
        		//console.log(data.score);
        		//$("#scoreTxt").text(data.score);
        		
        		$("#beforeStdgr").hide();
        		$("#afterStdgr").show();
        	}else{
        		alert("코너 만족도 참여 저장중 에러가 발생하였습니다.");
        	}
		},
		error:function(xhr){
			alert("코너 만족도 참여 저장중 에러가 발생하였습니다.");
		}
	});

}

function viewSatisfaction() {
	
	var f = document.getElementById("gSatisForm");
	var sysCd = f.sSysCd.value;
	var menuCd = f.sMenuCd.value;
	var cookName = sysCd+'|'+menuCd;
	var val = getCookie(cookName);
	if (val!=null && val.length > 0) {
		$("#beforeStdgr").hide();
		$("#afterStdgr").show();
	}else{
		$("#beforeStdgr").show();
		$("#afterStdgr").hide(); 
	}
}
 
function setCookie(name, value, expiredays){
    var todayDate = new Date();
    todayDate.setDate( todayDate.getDate() + expiredays );
    document.cookie = name + "=" + escape( value ) + "; path=/; expires=" + todayDate.toGMTString() + ";"
}

function getCookie(uName) {
    var flag = document.cookie.indexOf(uName+'=');
    if (flag != -1) {
        flag += uName.length + 1
        end = document.cookie.indexOf(';', flag)
        if (end == -1) end = document.cookie.length
        return unescape(document.cookie.substring(flag, end))
    }
}

</script>

<div class="comment_box">

    
    
    
        <div class="user_info">
			<span class="kcall">상담센터(1544-8080)</span>
			
				<span class="part"> 담당자 : 특허제도과 주상현 &vert; 042-481-8153
				
					 &vert; 최종수정일 : 2025-10-01
				
				</span>
			
			
			<span class="hide">공공누리 공공저작물 자유이용허락 출처표시</span>
		</div>

		<!-- 사용자 만족도 조사 시작-->
		<form id="gSatisForm" name="gSatisForm" target="SatisfactionFrame" onsubmit="setSatisfaction();">
		<!-- 22.03.28_ksh.호환성 오류(ID 중복) 조치, menuCd > sMenuCd, sysCd > sSysCd 로 수정 -->
		<input type="hidden" name="sMenuCd" id="sMenuCd" value='SCD0200111'>
		<input type="hidden" name="sSysCd" id="sSysCd" value='SCD02'>
		<input type="hidden" name="bultnId" id="bultnId" value=''>
		<!-- 23.07.07_lys.호환성 오류(ID 중복) 조치, ntatcSeq > sNtatcSeq 로 수정 -->
		<input type="hidden" name="sNtatcSeq" id="sNtatcSeq" value=''>
		
				<div id="beforeStdgr" class="user_comment"> 
					<h3>현재 페이지의 내용에 얼마나 만족하십니까?</h3>
					<div>
						<div class="custom-control custom-radio dp_02 mr10">
							<input type="radio" id="rbSatisfaction05" name="rbSatisfaction" value="5" class="custom-control-input">
							<label class="custom-control-label" for="rbSatisfaction05">매우만족</label>
						</div>
						<div class="custom-control custom-radio dp_02 mr10">
							<input type="radio" id="rbSatisfaction04" name="rbSatisfaction" value="4" class="custom-control-input">
							<label class="custom-control-label" for="rbSatisfaction04">만족</label>
						</div>
						<div class="custom-control custom-radio dp_02 mr10">
							<input type="radio" id="rbSatisfaction03" name="rbSatisfaction" value="3" class="custom-control-input">
							<label class="custom-control-label" for="rbSatisfaction03">보통</label>
						</div>
						<div class="custom-control custom-radio dp_02 mr10">
							<input type="radio" id="rbSatisfaction02" name="rbSatisfaction" value="2" class="custom-control-input">
							<label class="custom-control-label" for="rbSatisfaction02">불만족</label>
						</div>
						<div class="custom-control custom-radio dp_02">
							<input type="radio" id="rbSatisfaction01" name="rbSatisfaction" value="1" class="custom-control-input">
							<label class="custom-control-label" for="rbSatisfaction01">매우불만족</label>
						</div>
						&nbsp;&nbsp;
						
					</div>
					 
					 <div class="mt5">
		              <label for="commentText" class="hide">의견등록</label>
		              <input name="opinion" type="text" id="commentText" placeholder="이 페이지 이용 중 불편사항이나 기능오류 등 개선에 필요한 부분에 대한 의견을 주시면, 지속적으로 개선하겠습니다.">
		              <a href="javascript:setSatisfaction();" class="btn comment">의견등록</a>
					</div> 
					
				</div>
				
				<div id="afterStdgr" class="user_comment">
					<div>
						<p class="ct1 center mt10">귀하는 이미 만족도 조사에 응하셨습니다.</p>
					</div>
				</div>
		</form>
</div>

<!-- 사용자 만족도 조사 종료-->
<script>
	viewSatisfaction();
</script>
          			<!-- 만족도조사 : e -->	
          			
				</article>
			</div>
		</div>
	</div>
	<!--// container E--> 
	
	<!-- footer -->
	


<footer id="footer">
	<div class="footer_top">
		<div class="layout">
			<ul class="ft_list">
				
          		<li><a href="/kipo/kipoContentView.do?menuCd=SCD0201379" target="_blank" title="개인정보처리방침 바로가기 (새창)">개인정보처리방침</a></li>
				<li><a href="/kipo/kipoContentView.do?menuCd=SCD0200538" target="_blank" title="저작권정책 바로가기 (새창)">저작권정책</a></li>
				<li><a href="/kipo/kipoContentView.do?menuCd=SCD0200541" target="_blank" title="이메일무단수집거부 바로가기 (새창)">이메일무단수집거부</a></li>
				
				<li><a href="/ko/kpoContentView.do?menuCd=SCD0201249" title="바로가기">누리집이용안내 </a></li>
				<li><a href="/kipo/kipoContentView.do?menuCd=SCD0200540" target="_blank" title="특허서비스헌장 바로가기 (새창)">특허서비스헌장</a></li>
				<li><a href="https://privacy.kisa.or.kr/" target="_blank" title="개인정보침해신고 바로가기 (새창)">개인정보침해신고</a></li>
				<li><a href="/kipo/kipoContentView.do?menuCd=SCD0201126" target="_blank" title="최신 정보 자료 제공 서비스 바로가기 (새창)">최신 정보 자료 제공 서비스</a></li>
				<li><a href="/ko/hpErrorRcpt.do?menuCd=SCD0201102&parntMenuCd2=SCD0200409" title="누리집 불편사항접수 바로가기">누리집 불편사항접수</a></li>
				
				<li><a href="https://www.mois.go.kr/frt/sub/popup/p_taegugki_banner/screen.do" target="_blank" title="국가상징알아보기 바로가기 (새창)"><img src="/resource/images/kipo_header_flag.png" alt="대한민국 국기">국가상징알아보기</a></li>
			</ul>
		</div>
	</div>
	<div class="footer_bottom">
		<div class="layout">
			<div class="footer_logo">
				
				<span class="hide">지식재산처</span>
			</div>
			
			<address>
				
				
				
				
				<p>35208 대전광역시 서구 청사로 189 (서구 둔산동 920) 정부대전청사 4동 <span>대표전화 1544-8080(유료 / 월~금 09:00~18:00, 공휴일 제외)
				
				<a class="chaticon_01" href="https://chatbot.ips.go.kr/chatbotPop.ndo?bnrId=cuO6jXZLsIFMFrO" target="_blank" title="바로가기 (새창)">챗봇상담</a>
				<a class="chaticon_02" href="https://chat.patent.go.kr:10443/#/ttalk_main/KIPO_160635643985448436" target="_blank" title="바로가기 (새창)">채팅상담</a></span></p>
				
				<p class="copy">COPYRIGHT (C) MOIP. All Rights Reserved.</p>
			</address>
			<ul class="footer_mark">
				<li class="kogl"><a title="바로가기 (새창)" href="https://www.kogl.or.kr/" target="_blank"><img alt="공공누리 공공저작물 자유이용허락" src="/resource/images/bt_02.png"></a></li>
				
				
				<li class="web_access"><a title="바로가기 (새창)" href="http://www.wa.or.kr/board/list.asp?search=link_url&SearchString=www.kipo.go.kr&BoardID=0006" target="_blank"><img class="wa" alt="(사)한국장애인단체총연합회 한국웹접근성인증평가원 웹 접근성 우수사이트 인증마크(WA인증마크)" src="/resource/images/bt_01.png"></a></li>
			</ul>
			
			
		</div>
	</div>
</footer>
	<!--// footer E-->
	
</div>
</body>
</html>

