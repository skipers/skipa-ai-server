


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
<script src="/resource/js/jquery-1.12.2.min.js"></script>
<script src="/resource/js/jquery-ui.min.js"></script>
<script src="/resource/js/kipo_ui.min.js"></script>
<script src="/resource/js/keywordValidator.js"></script>

<script src="/resource/vendor/flatpickr/flatpickr.min.js"></script>
<script src="/resource/vendor/flatpickr/ko.js"></script>

<script>
	$(document).ready(function() {
		
		var mailPopYn = '';
		if(mailPopYn == 'Y'){
			$("#modalOpen").trigger('click');
		}
		
		//기간
		var flatpickrDemo = {
			init : function init() {
				this.bindUIActions();
			},
			bindUIActions : function bindUIActions() {
				this.handleFlatpickr();
			},
			_fp1 : function _fp1() {
				return flatpickr('#searchDateStart', {
					locale:"ko", dateFormat: "Y-m-d", allowInput : true, disableMobile:"true"
				});
			},
			_fp2 : function _fp1() {
				return flatpickr('#searchDateEnd', {
					locale:"ko", dateFormat: "Y-m-d", allowInput : true, disableMobile:"true"
				});
			},
			handleFlatpickr : function handleFlatpickr() {
				this._fp1();
				this._fp2();
			}
		};
		
		flatpickrDemo.init();

		var dt = new Date();
		var year;
		var com_year = dt.getFullYear();
		var searchYear = '';
		
		$("#searchYear").append("<option value='' >전체</option>");
	 	for(var y = (com_year-8); y <= (com_year); y++){
	 		if(searchYear == y){
	 			$("#searchYear").append("<option value='"+y+"'  selected=selected>"+y+"년</option>");
	 		}else{
	 			$("#searchYear").append("<option value='"+y+"'>"+y+"년</option>");
	 		}
	 	}

	});
	
	function fnumber(obj){
		if(obj.value.replace(/[0-9 \-]/g,"").length == 0){
			let ber = obj.value.replace(/[^0-9]/g,"");
			let ymd ="";
			
			if(ber.length < 4){
				return ber;
			}else if (ber.length < 6){
				ymd +=ber.substr(0,4);
				ymd +='-';
				ymd +=ber.substr(4);
			}else {
				ymd +=ber.substr(0,4);
				ymd +='-';
				ymd +=ber.substr(4,2);
				ymd +='-';
				ymd +=ber.substr(6);
			}
			
			if(ymd.length > 10){
				ymd = ymd.substr(0,10);
			}
			ymd = ymd.replace(/[^0-9 ^\-]/g,"");
			obj.value=ymd;
		}else{
			alert('숫자 이외의 값은 입력하실 수 없습니다.')
			obj.value = obj.value.replace(/[^0-9 ^\-]/g,"");
			return false;
		}
	}
	function checkSearch() {
		//26.03.31 주요활동인 경우에는 분류나 검색어 둘중 하나만 입력되어있으면 검색되게 수정
		var isBunRyu = false;
		
		if($("#menuCd").val() == "SCD0200655" && $("#searchBultn").val() != "") { 
			isBunRyu = true;
		}
		
		if($.trim($("#keyword").val()) == "" && !isBunRyu) {
			alert("검색어를 입력해주세요.");
			$("#keyword").focus();
			return false;
		}
		
		var start = $('#searchDateStart').val();
		var end = $('#searchDateEnd').val();
		
		if(start != '' && start != null){
			if(end == '' || end == null ){
				alert('종료일자를 입력해주세요.');
				return false;
			}
		}
		
		if(end != '' && end != null){
			if(start == '' || start == null ){
				alert('시작일자를 입력해주세요.');
				return false;
			}
		}
		
		start = start.replace(/-/gi,'');
		end = end.replace(/-/gi,'');
		
		if(start > end){
			alert('시작일자가 종료일자보다 클 수 없습니다.');
			return false;
		}
		
		return true;
	}

	/* pagination 페이지 링크 function */
	function fn_egov_link_page(pageNo){
		//26.01.22 검색어를 입력하지 않고 검색하는 것을 방지하는 기능 추가로 페이징 기능 사용할 때 검색어 체크는 필요 없어보여 주석처리 
		//if(!checkSearch()){return;}

		document.listForm.pageUnit.value = $("#cntPerPage").val();
		document.listForm.pageIndex.value = pageNo;
	   	document.listForm.submit();
	   	
	}

	function searchBoard(){
		if(!checkSearch()){return;}
		
		if(document.listForm.searchDateStart.value.length != 10 && document.listForm.searchDateStart.value.length != 0){
			alert('올바른 날짜 형식이 아닙니다.');
			return false;
		}
		
		if(document.listForm.searchDateEnd.value.length != 10 && document.listForm.searchDateEnd.value.length != 0){
			alert('올바른 날짜 형식이 아닙니다.');
			return false;
		}
		
		document.listForm.keyword.value = $("#keyword").val();
	   	document.listForm.submit();
	}
	
	function restBoard(cd){
		document.listForm.searchDateStart.value = '';
		document.listForm.searchDateEnd.value = '';
		document.listForm.searchCondition.value = '1';
		document.listForm.keyword.value = '';
		if(cd == 'SCD0200655'){
			document.listForm.searchBultn.value = '';	
		}
	   	document.listForm.submit();
	}

	function listFileDown(ntatcSeq,ntatcAtflSeq,aprchId){
		document.forms.detailFrm.ntatcSeq.value=ntatcSeq;
		document.forms.detailFrm.ntatcAtflSeq.value=ntatcAtflSeq;
		document.forms.detailFrm.aprchId.value=aprchId;
		document.forms.detailFrm.action = "/ko/kpoBultnFileDown.do";
		document.forms.detailFrm.submit();
	}
	
	function detail(ntatcSeq,aprchId){
		document.forms.detailFrm.ntatcSeq.value=ntatcSeq;
		document.forms.detailFrm.aprchId.value=aprchId;
		document.forms.detailFrm.action ="/ko/kpoBultnDetail.do";
		document.forms.detailFrm.submit();
	}
	
	function selectDomain(val){
		if(val == "directly"){
			$('#emailsvr').attr('disabled',false);
			$('#emailsvr').val('');
		}else{
			$('#emailsvr').attr('disabled',true);
			$('#emailsvr').val(val);
		}	
	}
	
	function mailSubmit(val){
		var confirmMsg;
		var emailIn = $('#emailIn').val();
		var emailsvr = $('#emailsvr').val();
		var domain = document.getElementById("domain");
		var boardIdList;
		var cnt=0;

		domain = domain.options[domain.selectedIndex].value;
		
		if(val == 'C'){
			confirmMsg = '신청';
		}else{
			confirmMsg = '해지';
		}

		$("input:checkbox[name=board_id]").each(function(){
			if(this.checked){
// 				boardIdList.push(this.value);
				if(cnt == 0){
					boardIdList = this.value;
				}else{
					boardIdList += ","+ this.value;
				}
				cnt++;
			}
		});
		
		if(boardIdList == '' || boardIdList == null){
			if(val == "C"){
			alert('수신 메일링 게시물을 선택하세요.');
			return false; 
			}
		}
		
		if($("#emailIn").val() == ''){
			alert('이메일을 입력하세요.');
			$("#emailIn").focus();
			return false;
		}else if(domain == '' || domain == null){
			alert('도메인을 입력하세요.');
			return false;
		}else{
			if(domain == 'directly'){
				domain = emailsvr;
				if(emailsvr == '' || emailsvr == null){
					alert('도메인을 입력하세요.');
					return false;
				}
			}
			
			var emadr = $("#emailIn").val() + "@" + domain;
			var regExp = /^[0-9a-zA-Z]([-_.]?[0-9a-zA-Z])*@[0-9a-zA-Z]([-_.]?[0-9a-zA-Z])*.[a-zA-Z]{2,3}$/i;
			
		 	if(!emadr.match(regExp)){
		 	   	alert("이메일을 다시 입력하세요.");
		 	  	return false;
		 	}
		}
		
		//26.01.29.jnh 개인정보 수집·이용 동의/미동의 버튼으로 변경 및 미동의시 문구 수정
		if(!$('input:radio[id="checkInY"]').is(":checked") && val == "C") {
			alert("개인정보 수집·이용 미동의시 신청이 불가합니다.");
			$('#checkInY').focus();
			return;
		} else {
			if(confirm('메일링서비스를 '+confirmMsg+'하시겠습니까?')){
				var param = {'boardIdList' : boardIdList , 'emadr' : emadr, 'type' : val};
				$.ajax({
					type:"post",
			        contentType : "application/json",
			        url:"/ko/kpoMail.do",
			        data : JSON.stringify(param),	        
			        dataType:'json',
					//traditional :true, 
			        success:function(data){
			        	if(data.success == "yes") {
			        		alert("정상적으로 처리되었습니다.");
			        		$("#appClose").trigger('click');
			        		// 신청/해지 시 데이터 초기화
			        		$('.p_con input').each(function() {
								if($(this).context.type == 'checkbox'){ //수신메일링 초기화
									$(this).context.checked = false;
								}else{
									if($(this).context.id == 'emailsvr'){ //텍스트 초기화
									    $(this).context.disabled = true;	
									}
									$(this).context.value = '';
								}
								if($(this).context.type == 'radio'){ //26.01.29 동의/미동의 라디오버튼 초기화
									$(this).context.checked = false;
								}
			        		});
			        		
		                    $('#domain').val('').prop('selected', true); //도메인 초기화
	
		                    $('.p_con').scrollTop(0); //스크롤 맨 위로 올리기
			        	} else if (data.success == "fail") {
							alert("작성하신 내용에 금지어(" + data.badWords.join(", ") + ")가 포함되어 있습니다. 확인 후 다시 시도해주세요."); //검출된 경우 서버에서 넣어준 badWords 목록을 나열해주기
						} else {
			        		alert("처리 중 오류가 발생했습니다.");
			        	}
					},
					error:function(xhr){
						alert("처리 중 오류가 발생했습니다.");
					}
				});
			}
		}
	}
	
	function setCntPerPage() {
		document.listForm.pageUnit.value = $('#cntPerPage').val();
	   	document.listForm.submit();
	}
</script>


	<title>지식재산처 >
			
				
					지식재산제도 > 
					
				
			
				
					산업재산권 등록제도 > 
					
				
			
				
					자료실 > 
					
				
			
				
					
					첨부서류 양식(목록)
				
			
	</title>



</head>
<body> 
<!-- 본문바로가기 -->
<div id="skip"><a href="#content">본문 바로가기</a><a href="#gnb">주메뉴 바로가기</a></div>
<div id="wrap"> 
	
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
			
			
           		
            	
            	
            	
            	
            	
           	
           	<li><a href="/ko/kpoContentView.do?menuCd=SCD0200111"   >
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
				<li><a href="SCD0200198" class="on">자료실</a>
					<ul>
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200635&parntMenuCd2=SCD0200198"   >
	              		예규,지침</a></li>
					
					
					<!-- 4depth loop start -->
					
					
					
					
					
					
					
					
					
					
					
	              		
		            	
		            	
		            	
		            	
		            	
	              	
	              	<li><a href="/ko/kpoBultnMgmt.do?menuCd=SCD0200636&parntMenuCd2=SCD0200198"  class="on" >
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
					<h2 data-brl-use="PT">첨부서류 양식</h2>
					<ul class="location">
						<li class="home"><span><a href="/">HOME</a></span></li>
						
						
						<li class="depth1">
							<span>
							
								<a href="/ko/naviMenuLink.do?menuCd=SCD0200109">지식재산제도</a>
								
							
							</span>
						</li>
						
						
						<li class="depth1">
							<span>
							
								<a href="/ko/naviMenuLink.do?menuCd=SCD0200194">산업재산권 등록제도</a>
								
							
							</span>
						</li>
						
						
						<li class="depth1">
							<span>
							
								<a href="/ko/naviMenuLink.do?menuCd=SCD0200198">자료실</a>
								
							
							</span>
						</li>
						
						
						<li class="depth1">
							<span>
							
								
								첨부서류 양식
							
							</span>
						</li>
						
					</ul>
					
					<div class="locate_btn">
						<button class="sns_btn" onclick="sns()"><span class="hide">sns공유하기(페이스북,X,밴드,카카오스토리)</span><i class="fa fa-share-alt" title="SNS공유하기"></i></button>
						<div class="sns_btns sns_btns_braille" id="sns">
							<a href="javascript:shareSNS('f','첨부서류 양식','/ko/kpoBultnMgmt.do?menuCd=SCD0200636&parntMenuCd2=SCD0200198');" title="페이스북 첨부서류 양식 공유하기 새창 열림"><img src="/resource/images/sns_fb_b.png" alt="페이스북 공유하기 새창 열림"></a>
							<a href="javascript:shareSNS('t','첨부서류 양식','/ko/kpoBultnMgmt.do?menuCd=SCD0200636&parntMenuCd2=SCD0200198');" title="X 첨부서류 양식 공유하기 새창 열림"><img src="/resource/images/sns_tw_b.png" alt="X 공유하기 새창 열림"></a>
							<a href="javascript:shareSNS('b','첨부서류 양식','/ko/kpoBultnMgmt.do?menuCd=SCD0200636&parntMenuCd2=SCD0200198');" title="밴드 첨부서류 양식 공유하기 새창 열림"><img src="/resource/images/sns_blog_b.png" alt="밴드 공유하기 새창 열림"></a>
							<a href="javascript:shareSNS('k','첨부서류 양식','/ko/kpoBultnMgmt.do?menuCd=SCD0200636&parntMenuCd2=SCD0200198');" title="카카오스토리 첨부서류 양식 공유하기 새창 열림"><img src="/resource/images/sns_kakao_b.png" alt="카카오스토리 공유하기 새창 열림"></a>
							<button class="close_btn" onclick="sns()"><i class="fa fa-times" title="SNS공유하기 닫기"></i><span class="hide">SNS공유하기 닫기</span></button>
						</div>
						
						
						
						<button class="print_btn" onclick="window.print()"><i class="fa fa-print" title="인쇄하기"></i></button>
						<button class="brailleviewer_btn" onclick="openBrlViewer('지식재산처 > 지식재산제도 > 산업재산권 등록제도 > 자료실 > 첨부서류 양식')"><span class="fa braille_viewer" title="전자점자뷰어보기(새창열림)"></span></button>
						<button class="brailledown_btn" onclick="exportBrl('brl', '지식재산처 > 지식재산제도 > 산업재산권 등록제도 > 자료실 > 첨부서류 양식')"><span class="fa braille_down" title="전자점자다운로드"></span></button>
					</div>
				</div>
				<article class="txt">
				
				<!-- 5차 탭메뉴 : s -->
					
					<!-- 5차 탭메뉴 : e -->
					
		<!-- 최근개정법령 배너 운영 계약현황 s-->
		
		<!--최근개정법령 배너  운영 계약현황 e-->

        <!-- 페이지설명 : s -->
		
		<div class="page_info">
				<h3>FAQ 자료를 제공하는 게시판입니다.</h3><ul><li>날짜를 입력하여 자료를 검색하거나, 첨부된 자료를 다운로드 할 수 있습니다.</li><li>기간으로 조회할 경우 2020년 1월 1일은 20200101으로 입력하시기 바랍니다.</li></ul>
		</div>
		
		
		<!--국회관련(국정감사) 운영  s-->		
		
		<!--국회관련(국정감사) 운영 e-->
        
        <!-- 검색 : s -->   
          <div class="defSchWrap">
            <div class="defSchBox">
              <div class="defSch">
				<form id="listForm" name="listForm" action="/ko/kpoBultnMgmt.do" >
				<input type="hidden" id="pageIndex" name="pageIndex" value="">
				<input type="hidden" id="pageUnit" name="pageUnit" value="">
				<input type="hidden" id="curMenuCd" name="curMenuCd" value="">
				<input type="hidden" id="menuCd" name="menuCd" value="SCD0200636">
				<input type="hidden" id="sysCd" name="sysCd" value="SCD02">
				<input type="hidden" id="parntMenuCd2" name="parntMenuCd2" value="SCD0200198">
			
				
				
				 		
				 
					
				 
					
				 
					
				 
					
										 		
					
				 
					
				 
					
				 
				
				<div class="defDate">
					<label for="searchDateStart" class="hide">기간검색: 시작일자</label>
			    	<input id="searchDateStart" name="searchDateStart" type="text" class="cal" title="시작일자 입력 예시 : 20250101" value="" maxlength="10" onkeyup="fnumber(this);">
			    	<label for="searchDateEnd" class="hide">기간검색: 종료일자</label> 
			    	<input id="searchDateEnd" name="searchDateEnd" type="text" class="cal" title="종료일자 입력 예시 : 20250101" value="" maxlength="10" onkeyup="fnumber(this);">
				</div>
                <label for="searchCondition" class="hide">검색항목 선택</label>
             	<select  title="검색항목선택" id="searchCondition" name="searchCondition">
					<option value="1" >제목</option>
					<option value="2"  >내용</option>
					
						<option value="3"  >담당부서</option>
					
					
				</select>
                <label for="keyword" class="hide">검색어 입력</label>
                <input type="text"   placeholder="검색어" name="keyword" id="keyword" value="">
                
                
                
                <a href="#" class="btn srch" onclick="searchBoard();">검색</a>
                
                <a href="#" class="btn cancel" onclick="restBoard('SCD0200636');">검색취소</a>
               </form>
              </div>
            </div>
          </div>
          <!-- 검색 : e -->
          <!-- 리스트 : s -->
		<div>
          	<div class="countWrap"> <!-- 건별 보기 기능 추가 : s -->
          		<div class="countBox">
					<span class="cnt_sp">총 : 25건, 1/3(Page)</span>
					<span>
					
						<label for="cntPerPage" class="hide">목록 건 보기</label>
						<select  title="목록 건 보기" id="cntPerPage" name="cntPerPage" class="defSch select">
							<option value="10"  >10건 보기</option>
							<option value="20"  >20건 보기</option>
							<option value="30"  >30건 보기</option>
							<option value="50"  >50건 보기</option>
							<option value="100"  >100건 보기</option>					
						</select>
						<a href="#" class="btn srch"  onclick="setCntPerPage();">선택</a>
					</span>
				</div>
			</div> <!-- 건별 보기 기능 추가 : e -->
            <table class="tbl_list" data-brl-use="TH" data-brl-tbltype=1>
            	
				<caption>첨부서류 양식 목록의 번호, 제목, 파일, 담당부서, 작성일, 조회수를 나타낸 표입니다.</caption>
				<thead>
					<tr>
				    
			    		
				    		
			    			
			    			
				    		
				    		

							   	<th scope="col">번호</th>		

				    		
				    	
					
			    		
				    		
				    			<th scope="col" class="bbs_tit">제목</th>
				    		
			    			
			    			
				    		
				    		
				    	
					
			    		
				    		
			    			
			    			
				    		
				    		

							   	<th scope="col">파일</th>		

				    		
				    	
					
			    		
				    		
			    			
			    			
				    		
				    		

							   	<th scope="col">담당부서</th>		

				    		
				    	
					
			    		
				    		
			    			
				    			<th scope="col" class="bbs_date">작성일</th>
				    		
			    			
				    		
				    		
				    	
					
			    		
				    		
			    			
			    			
				    		
				    		

							   	<th scope="col">조회수</th>		

				    		
				    	
					
					</tr>
				</thead>
				<tbody>
                
					
						
							
							<tr> 
							
								
									
									<td>
										25
									
									
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									<td class="bbs_tit">
										

<!-- 								23.10.19 김승현 주무관님 요청으로 .do 뒤 파라미터 보이게 url 형식 변경 -->
										
										<a href="/ko/kpoBultnDetail.do?menuCd=SCD0200636&ntatcSeq=1265&sysCd=SCD02&aprchId=BUT0000044" title="등록신청에 필요한 첨부서류 양식(사용인감계)" >등록신청에 필요한 첨부서류 양식(사용인감계)</a>
									
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									<td>
									
										
									
										
									
										
									
										
									
										
									
										
									
										
									
										
									
										
									
										
										<!-- 23.09.11 첨부파일 url 형식 변경  -->
										<a href="/ko/kpoBultnFileDown.do?ntatcSeq=1265&ntatcAtflSeq=1&sysCd=SCD02&aprchId=BUT0000044" title="사용인감계.hwp 다운로드">

											
											<img src="/resource/images/ico_hwp.gif" width="16" height="16" alt="HWP 첨부파일">
										</a>
										
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									<td>
										산업재산등록과
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									
									
									<td class="bbs_date">
<!-- 										화면표시일 우선 없으면 작성일  -->
										
											
											2016-04-15 
												
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									
									<td>
										9728 
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
						</tr>
						
							
							<tr> 
							
								
									
									<td>
										24
									
									
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									<td class="bbs_tit">
										

<!-- 								23.10.19 김승현 주무관님 요청으로 .do 뒤 파라미터 보이게 url 형식 변경 -->
										
										<a href="/ko/kpoBultnDetail.do?menuCd=SCD0200636&ntatcSeq=1264&sysCd=SCD02&aprchId=BUT0000044" title="등록신청에 필요한 첨부서류 양식(상속 재산분할 협의서)" >등록신청에 필요한 첨부서류 양식(상속 재산분할 협의서)</a>
									
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									<td>
									
										
									
										
									
										
									
										
									
										
									
										
									
										
									
										
									
										
										<!-- 23.09.11 첨부파일 url 형식 변경  -->
										<a href="/ko/kpoBultnFileDown.do?ntatcSeq=1264&ntatcAtflSeq=1&sysCd=SCD02&aprchId=BUT0000044" title="상속 재산분할 협의서.hwp 다운로드">

											
											<img src="/resource/images/ico_hwp.gif" width="16" height="16" alt="HWP 첨부파일">
										</a>
										
									
										
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									<td>
										산업재산등록과
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									
									
									<td class="bbs_date">
<!-- 										화면표시일 우선 없으면 작성일  -->
										
											
											2016-04-15 
												
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									
									<td>
										19867 
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
						</tr>
						
							
							<tr> 
							
								
									
									<td>
										23
									
									
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									<td class="bbs_tit">
										

<!-- 								23.10.19 김승현 주무관님 요청으로 .do 뒤 파라미터 보이게 url 형식 변경 -->
										
										<a href="/ko/kpoBultnDetail.do?menuCd=SCD0200636&ntatcSeq=1263&sysCd=SCD02&aprchId=BUT0000044" title="등록신청에 필요한 첨부서류 양식(신탁재산 인계증서)" >등록신청에 필요한 첨부서류 양식(신탁재산 인계증서)</a>
									
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									<td>
									
										
									
										
									
										
									
										
									
										
									
										
									
										
									
										
										<!-- 23.09.11 첨부파일 url 형식 변경  -->
										<a href="/ko/kpoBultnFileDown.do?ntatcSeq=1263&ntatcAtflSeq=1&sysCd=SCD02&aprchId=BUT0000044" title="신탁재산 인계증서.hwp 다운로드">

											
											<img src="/resource/images/ico_hwp.gif" width="16" height="16" alt="HWP 첨부파일">
										</a>
										
									
										
									
										
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									<td>
										산업재산등록과
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									
									
									<td class="bbs_date">
<!-- 										화면표시일 우선 없으면 작성일  -->
										
											
											2016-04-15 
												
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									
									<td>
										3501 
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
						</tr>
						
							
							<tr> 
							
								
									
									<td>
										22
									
									
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									<td class="bbs_tit">
										

<!-- 								23.10.19 김승현 주무관님 요청으로 .do 뒤 파라미터 보이게 url 형식 변경 -->
										
										<a href="/ko/kpoBultnDetail.do?menuCd=SCD0200636&ntatcSeq=1262&sysCd=SCD02&aprchId=BUT0000044" title="등록신청에 필요한 첨부서류 양식(신탁계약서)" >등록신청에 필요한 첨부서류 양식(신탁계약서)</a>
									
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									<td>
									
										
									
										
									
										
									
										
									
										
									
										
									
										
										<!-- 23.09.11 첨부파일 url 형식 변경  -->
										<a href="/ko/kpoBultnFileDown.do?ntatcSeq=1262&ntatcAtflSeq=1&sysCd=SCD02&aprchId=BUT0000044" title="신탁계약서.hwp 다운로드">

											
											<img src="/resource/images/ico_hwp.gif" width="16" height="16" alt="HWP 첨부파일">
										</a>
										
									
										
									
										
									
										
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									<td>
										산업재산등록과
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									
									
									<td class="bbs_date">
<!-- 										화면표시일 우선 없으면 작성일  -->
										
											
											2016-04-15 
												
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									
									<td>
										3510 
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
						</tr>
						
							
							<tr> 
							
								
									
									<td>
										21
									
									
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									<td class="bbs_tit">
										

<!-- 								23.10.19 김승현 주무관님 요청으로 .do 뒤 파라미터 보이게 url 형식 변경 -->
										
										<a href="/ko/kpoBultnDetail.do?menuCd=SCD0200636&ntatcSeq=1261&sysCd=SCD02&aprchId=BUT0000044" title="등록신청에 필요한 첨부서류 양식(양도담보 설정계약 해제증서)" >등록신청에 필요한 첨부서류 양식(양도담보 설정계약 해제증서)</a>
									
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									<td>
									
										
									
										
									
										
									
										
									
										
									
										
										<!-- 23.09.11 첨부파일 url 형식 변경  -->
										<a href="/ko/kpoBultnFileDown.do?ntatcSeq=1261&ntatcAtflSeq=1&sysCd=SCD02&aprchId=BUT0000044" title="양도담보 설정계약 해제증서.hwp 다운로드">

											
											<img src="/resource/images/ico_hwp.gif" width="16" height="16" alt="HWP 첨부파일">
										</a>
										
									
										
									
										
									
										
									
										
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									<td>
										산업재산등록과
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									
									
									<td class="bbs_date">
<!-- 										화면표시일 우선 없으면 작성일  -->
										
											
											2016-04-15 
												
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									
									<td>
										4034 
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
						</tr>
						
							
							<tr> 
							
								
									
									<td>
										20
									
									
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									<td class="bbs_tit">
										

<!-- 								23.10.19 김승현 주무관님 요청으로 .do 뒤 파라미터 보이게 url 형식 변경 -->
										
										<a href="/ko/kpoBultnDetail.do?menuCd=SCD0200636&ntatcSeq=1260&sysCd=SCD02&aprchId=BUT0000044" title="등록신청에 필요한 첨부서류 양식(양도담보 특허권 반환증서)" >등록신청에 필요한 첨부서류 양식(양도담보 특허권 반환증서)</a>
									
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									<td>
									
										
									
										
									
										
									
										
									
										
										<!-- 23.09.11 첨부파일 url 형식 변경  -->
										<a href="/ko/kpoBultnFileDown.do?ntatcSeq=1260&ntatcAtflSeq=1&sysCd=SCD02&aprchId=BUT0000044" title="양도담보 특허권 반환증서.hwp 다운로드">

											
											<img src="/resource/images/ico_hwp.gif" width="16" height="16" alt="HWP 첨부파일">
										</a>
										
									
										
									
										
									
										
									
										
									
										
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									<td>
										산업재산등록과
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									
									
									<td class="bbs_date">
<!-- 										화면표시일 우선 없으면 작성일  -->
										
											
											2016-04-15 
												
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									
									<td>
										3658 
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
						</tr>
						
							
							<tr> 
							
								
									
									<td>
										19
									
									
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									<td class="bbs_tit">
										

<!-- 								23.10.19 김승현 주무관님 요청으로 .do 뒤 파라미터 보이게 url 형식 변경 -->
										
										<a href="/ko/kpoBultnDetail.do?menuCd=SCD0200636&ntatcSeq=1259&sysCd=SCD02&aprchId=BUT0000044" title="등록신청에 필요한 첨부서류 양식(양도담보 설정계약서)" >등록신청에 필요한 첨부서류 양식(양도담보 설정계약서)</a>
									
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									<td>
									
										
									
										
									
										
									
										
										<!-- 23.09.11 첨부파일 url 형식 변경  -->
										<a href="/ko/kpoBultnFileDown.do?ntatcSeq=1259&ntatcAtflSeq=1&sysCd=SCD02&aprchId=BUT0000044" title="양도담보 설정계약서.hwp 다운로드">

											
											<img src="/resource/images/ico_hwp.gif" width="16" height="16" alt="HWP 첨부파일">
										</a>
										
									
										
									
										
									
										
									
										
									
										
									
										
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									<td>
										산업재산등록과
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									
									
									<td class="bbs_date">
<!-- 										화면표시일 우선 없으면 작성일  -->
										
											
											2016-04-15 
												
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									
									<td>
										4392 
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
						</tr>
						
							
							<tr> 
							
								
									
									<td>
										18
									
									
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									<td class="bbs_tit">
										

<!-- 								23.10.19 김승현 주무관님 요청으로 .do 뒤 파라미터 보이게 url 형식 변경 -->
										
										<a href="/ko/kpoBultnDetail.do?menuCd=SCD0200636&ntatcSeq=1257&sysCd=SCD02&aprchId=BUT0000044" title="등록신청에 필요한 첨부서류 양식(권리 포기서)" >등록신청에 필요한 첨부서류 양식(권리 포기서)</a>
									
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									<td>
									
										
									
										
									
										
										<!-- 23.09.11 첨부파일 url 형식 변경  -->
										<a href="/ko/kpoBultnFileDown.do?ntatcSeq=1257&ntatcAtflSeq=1&sysCd=SCD02&aprchId=BUT0000044" title="권리 포기서.hwp 다운로드">

											
											<img src="/resource/images/ico_hwp.gif" width="16" height="16" alt="HWP 첨부파일">
										</a>
										
									
										
									
										
									
										
									
										
									
										
									
										
									
										
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									<td>
										산업재산등록과
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									
									
									<td class="bbs_date">
<!-- 										화면표시일 우선 없으면 작성일  -->
										
											
											2016-04-15 
												
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									
									<td>
										6786 
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
						</tr>
						
							
							<tr> 
							
								
									
									<td>
										17
									
									
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									<td class="bbs_tit">
										

<!-- 								23.10.19 김승현 주무관님 요청으로 .do 뒤 파라미터 보이게 url 형식 변경 -->
										
										<a href="/ko/kpoBultnDetail.do?menuCd=SCD0200636&ntatcSeq=1256&sysCd=SCD02&aprchId=BUT0000044" title="등록신청에 필요한 첨부서류 양식(공유자 동의서)" >등록신청에 필요한 첨부서류 양식(공유자 동의서)</a>
									
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									<td>
									
										
									
										
										<!-- 23.09.11 첨부파일 url 형식 변경  -->
										<a href="/ko/kpoBultnFileDown.do?ntatcSeq=1256&ntatcAtflSeq=1&sysCd=SCD02&aprchId=BUT0000044" title="공유자 동의서.hwp 다운로드">

											
											<img src="/resource/images/ico_hwp.gif" width="16" height="16" alt="HWP 첨부파일">
										</a>
										
									
										
									
										
									
										
									
										
									
										
									
										
									
										
									
										
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									<td>
										산업재산등록과
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									
									
									<td class="bbs_date">
<!-- 										화면표시일 우선 없으면 작성일  -->
										
											
											2016-04-15 
												
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									
									<td>
										6076 
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
						</tr>
						
							
							<tr> 
							
								
									
									<td>
										16
									
									
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									<td class="bbs_tit">
										

<!-- 								23.10.19 김승현 주무관님 요청으로 .do 뒤 파라미터 보이게 url 형식 변경 -->
										
										<a href="/ko/kpoBultnDetail.do?menuCd=SCD0200636&ntatcSeq=1255&sysCd=SCD02&aprchId=BUT0000044" title="등록신청에 필요한 첨부서류 양식(단독신청 승낙서)" >등록신청에 필요한 첨부서류 양식(단독신청 승낙서)</a>
									
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									<td>
									
										
										<!-- 23.09.11 첨부파일 url 형식 변경  -->
										<a href="/ko/kpoBultnFileDown.do?ntatcSeq=1255&ntatcAtflSeq=1&sysCd=SCD02&aprchId=BUT0000044" title="단독신청 승낙서.hwp 다운로드">

											
											<img src="/resource/images/ico_hwp.gif" width="16" height="16" alt="HWP 첨부파일">
										</a>
										
									
										
									
										
									
										
									
										
									
										
									
										
									
										
									
										
									
										
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									<td>
										산업재산등록과
									
									
									
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									
									
									<td class="bbs_date">
<!-- 										화면표시일 우선 없으면 작성일  -->
										
											
											2016-04-15 
												
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
								
									
									
									
									
									
									
									<td>
										2999 
									
									
									
									
									
									
											
									
																
									
									
												
									
												
									
													
									
												
									
												
									
											
									
													
									
												
									
										
									
									
									
									
								</td>
							
						</tr>
																	
					
    			
				
				</tbody>
			</table>
		</div>
          <!-- 리스트 : e -->
          <!-- 페이징 : s -->
            <!-- pc -->
	          <div class="pagination">
	          	<strong>1</strong>&#160;<a href="#" onclick="fn_egov_link_page(2); return false;" title="2">2</a>&#160;<a href="#" onclick="fn_egov_link_page(3); return false;" title="3">3</a>&#160;

	          </div>
	          
	          <!-- mobile -->
	          <div class="pagenation pageNum"> 
	          	
	          	
	            
	            <span class="currentPage"><em>1</em>/3</span>
	            
	            
	            <a href="javascript:fn_egov_link_page('2');" class="next">다음 페이지로</a>
	            
	          </div>
          <!-- 페이징 : e -->
          
          <!-- 버튼 : s -->
          <div class="btnAreaLR">
            <div class="btnA_r">
              
            </div>
          </div>
          <!-- 버튼 : e -->
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
        	menuCd:'SCD0200636',
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
			
				<span class="part"> 담당자 : 지식재산등록과 장지욱 &vert; 042-481-5244
				
				</span>
			
			
			<span class="hide">공공누리 공공저작물 자유이용허락 출처표시</span>
		</div>

		<!-- 사용자 만족도 조사 시작-->
		<form id="gSatisForm" name="gSatisForm" target="SatisfactionFrame" onsubmit="setSatisfaction();">
		<!-- 22.03.28_ksh.호환성 오류(ID 중복) 조치, menuCd > sMenuCd, sysCd > sSysCd 로 수정 -->
		<input type="hidden" name="sMenuCd" id="sMenuCd" value='SCD0200636'>
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
	
	
	 	<form action="/ko/kpoBultnDetail.do" name="detailFrm" id="detailFrm" method="post">
	        <input type="hidden" name="ntatcSeq" value="">
	        <input type="hidden" name="searchCondition" value="">
	        <input type="hidden" name="pageIndex" value="1">
	        <input type="hidden" name="keyword" value="">
	        <input type="hidden" name="curMenuCd" value="">
	        <input type="hidden" name="paramSearchDateStart" value="">
	        <input type="hidden" name="paramSearchDateEnd" value="">
	        <input type="hidden" name="parntMenuCd2" value="SCD0200198">
	        <input type="hidden" name="aprchId" value="">
	        <input type="hidden" name="sysCd" value="SCD02">
	        <input type="hidden" name="menuCd" value="SCD0200636">
	        <input type="hidden" name="searchYear" value="">
	        <input type="hidden" name="ntatcAtflSeq" value="">
	        
        </form>
</div> 
</body>
</html>