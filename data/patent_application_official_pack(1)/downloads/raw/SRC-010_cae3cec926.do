






    
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="X-UA-Compatible" content="ie=edge">
<link rel="shortcut icon" href="/resource/images/favicon.ico" />







<!--  css Start -->
<link rel="stylesheet" href="/resource/css/common.css?v=2026052601">
<link rel="stylesheet" href="/resource/css/ipt_layout.css?v=2026052601">
<link rel="stylesheet" href="/resource/css/ipt_contents.css?v=2026052601">
<!--  js Start --> 
<script src="/resource/vendor/jquery/jquery.min.js"></script>
<script src="/resource/js/jquery-ui.min.js"></script>
<script src="/resource/js/ipt_ui.js"></script>
<script src="/resource/vendor/flatpickr/flatpickr.min.js"></script>
<script src="/resource/vendor/flatpickr/ko.js"></script>
<script src="/resource/vendor/slick/slick.min.js"></script>
<script src="/resource/js/keywordValidator.js"></script>



<script>
var imgPath = "/ko/imgViewUrl.do?";
var imgPath2 = "/ko/imageKpoUrlView.do?";

function mainMng(str) {
	var param = {};
	var trgUrl = "";
	if (str == "V") {
		param = {'sysCd' : 'SCD07'};
		trgUrl = "getVisualList.do";
	} else if (str == "P") {
		param = {'sysCd' : 'SCD07'};
		trgUrl = "getPopupList.do";
	}
	ajaxDataProc(param, trgUrl, str);
}

function ajaxDataProc(param, trgUrl, str) {
	$.ajax({
		type : "post",
		contentType : "application/json",
		url : trgUrl,
		data : JSON.stringify(param),
		dataType : 'json',
		success : function(data) {
			setDataBinding(data.list, str);
		},
		error : function(xhr) {
			console.log('ì¤ë¥ê° ë°ìíììµëë¤.\r\nê´ë¦¬ììê² ë¬¸ìí´ì£¼ì¸ì.');
		}
	});
}

function setDataBinding(obj, str) {
	var elemId1 = "", elemId2 = "", elemTag1 = "", elemTag2 = "";
	if (str == "V") {
		elemId1 = "visualList";
		elemId2 = "visualContList";
		var visualCnt = 0;

		if (obj.length > 0) {

			for (var i = 0; i < obj.length; i++) {

				var visualPath1 = imgPath + "sysCd=" + obj[i].SYS_CD + "&seq=" + obj[i].SEQ + "&jobGbn=VP";
				var visualPath2 = imgPath + "sysCd=" + obj[i].SYS_CD + "&seq=" + obj[i].SEQ + "&jobGbn=VM";
				elemTag1 += "<div class='slick-list draggable'>";
				elemTag1 += "<div class='slick-track'>";
				elemTag1 += "<div class='mainv_img slick-slide'>";

				if (obj[i].LINK_EXST_YN == "N") {
					elemTag1 += "<a href=\"javascript:goLink('" + obj[i].MENU_CNCT_URL + "','" + obj[i].VISUAL_TP + "','" + str + "')\">";
				} else {
					elemTag1 += "<a>";
				}
				elemTag1 += "<img src='"+visualPath1+"' alt='"+obj[i].RPLC_TXT+"' title='"+obj[i].RPLC_TXT+"' class='mv1'/>";
				elemTag1 += "<img src='"+visualPath2+"' alt='"+obj[i].RPLC_TXT_MOBILE+"' title='"+obj[i].RPLC_TXT_MOBILE+"' class='mv2'/>";
				elemTag1 += "</a></div></div></div>";
				if (obj[i].VISUAL_CONT != "N") {
					if (visualCnt < 5) {
						elemTag2 += "<li><a href=\"javascript:goVisualLink('" + i + "')\"><span>" + obj[i].VISUAL_CONT + "</sapn></a></li>";
					}
					visualCnt++;
				}
			}
			$('#' + elemId1).html(elemTag1);
			$('#' + elemId2).html(elemTag2);
			
			visualSlide();
		}
	} else if (str == "P") {

		if (obj.length > 0) {
			for (var p=0; p < obj.length; p++) {
				popAction(obj[p].POPUP_SORT,obj[p].SYS_CD,obj[p].SEQ,obj[p].RPLC_TXT,p,obj[p].MENU_CNCT_URL,obj[p].POPUP_TP);
			}
		}
	}
}

function popAction(sort,sysCd,seq,rtxt,idx,link,tp) {
	var lft = (document.body.offsetWidth/2) - 750;
		lft += window.screenLeft;
	var hgt = (document.body.offsetHeight/2) - 750;
	var rtxt = encodeURIComponent(rtxt);
	var rslt = getCookie(sysCd+seq);
	//22.05.03, íì ë°ë¡ê°ê¸°ì &ë¤ ë¬¸ì ì­ì ë¡ ì¸í URL ì¸ì½ë© ì¶ê°, ì¤ì ë¯¼
	var link = encodeURIComponent(link);
	if(idx == 1){
		lft = lft+450;
	}else if(idx == 2){
		lft = lft+900;
	}
	if(rslt != "N"){
		window.open("/ipt/winPopup.do?jobGbn=P&sysCd="+sysCd+"&seq="+seq, "winPopup"+idx, "top="+hgt+",left="+lft+",width=450,height=330,status=no,toolbar=no,menubar=no,location=no,scrollbars=no,resizable=yes");	
	}
}

function getCookie(key) {
	var rslt = "Y";
	var cookie = document.cookie;	
	if(cookie.length > 0){
		var strIdx = cookie.indexOf(key);
		var endIdx ="";
		if(strIdx > -1){
			strIdx += key.length;
			endIdx = cookie.indexOf(";",strIdx);
			if(endIdx == -1){
				endIdx = cookie.length;
			}
		}
		rslt = cookie.substring(strIdx+1,endIdx);
	}
	return rslt;
}

function visualSlide() {
	var slider = $('.main_visual');
	slider.on('init reInit afterChange', function(event, slick, currentSlide, nextSlide) {
		var i = (currentSlide ? currentSlide : 0) + 1;
		$('.count').text(i + '/' + slick.slideCount);
	});

	slider.slick({
		autoplay : true,
		autoplaySpeed : 5000,
		prevArrow : $('.prevArrow'),
		nextArrow : $('.nextArrow')
	});
	$('.button.stop').click(function() {
				slider.addClass('paused').slick('slickPause');
				$('.main_visual_banner .layout .mainv_btn button.play').css('display', 'block');
				$('.main_visual_banner .layout .mainv_btn button.stop').css('display', 'none');
	});
	$('.button.play').click(function() {
				slider.addClass('play').slick('slickPlay');
				$('.main_visual_banner .layout .mainv_btn button.stop').css('display', 'block');
				$('.main_visual_banner .layout .mainv_btn button.play').css('display', 'none');
	});
}

$(function(){
	$(".news_tab ul").each(function(){
		var tabMenu = $(this).children('.news_tabmenu');
		tabMenu.on('click focusin',function(){
			var idx = tabMenu.index(this);
			tabMenu.removeClass('on').eq(idx).addClass('on');
		});
	});
});
</script>

<title>특허심판원</title>
</head>
<body>
<!-- 본문바로가기 -->
<div id="skip"><a href="#content">본문 바로가기</a><a href="#gnb">주메뉴 바로가기</a></div>
<div id="wrap"> 

	<!-- header -->
  	


<script type="text/javascript">
	function linkOpen(target, url){
		if(target == '10301'){
			location.href = url;
		}else if(target == '10302'){
			window.open(url);
		}
	}
</script>

<header id="header" class="fixed"> 
	<div class="header-wrap">
		<div class="nav-wrap">
			<div class="layout">
				<h1 class="logo"><a href="/ipt">특허심판원</a></h1>
				<ul id="gnb">
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes start -->
            		<li class="th1"><a href="/ipt/topMenuLink.do?menuCd=SCD0400055"><span>특허심판제도 안내</span></a>
              			<ul class="depth2">
              		<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iptContentView.do?menuCd=SCD0400062">특허심판이란</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/topMenuLink.do?menuCd=SCD0400061">특허심판의 종류</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/topMenuLink.do?menuCd=SCD0400063">특허심판의 절차</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/topMenuLink.do?menuCd=SCD0400064">특허취소신청제도</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iptContentView.do?menuCd=SCD0400065">재심</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iptContentView.do?menuCd=SCD0400066">심결취소소송</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iptContentView.do?menuCd=SCD0400067">국선대리인 제도</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iptContentView.do?menuCd=SCD0401383">심판-조정연계 제도</a></li>
						
					
						</ul>
					</li>
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes start -->
            		<li class="th1"><a href="/ipt/topMenuLink.do?menuCd=SCD0400056"><span>소식알림</span></a>
              			<ul class="depth2">
              		<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400476&amp;parntMenuCd2=SCD0400056">심판원 알림사항</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0401342&amp;parntMenuCd2=SCD0400056">보도자료</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400478&amp;parntMenuCd2=SCD0400056">우리원 주요심결</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400479&amp;parntMenuCd2=SCD0400056">판례연구 우수논문집</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iptContentView.do?menuCd=SCD0400075">논문공모 명예의 전당</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0401170&amp;parntMenuCd2=SCD0400056">특허심판원 연보</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iptContentView.do?menuCd=SCD0401353">올해의 심판관</a></li>
						
					
						</ul>
					</li>
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes start -->
            		<li class="th1 on"><a href="/ipt/topMenuLink.do?menuCd=SCD0400058"><span>민원/참여</span></a>
              			<ul class="depth2">
              		<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iframe.do?menuCd=SCD0400480">민원신청</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iframe.do?menuCd=SCD0400481">나의민원확인</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iptContentView.do?menuCd=SCD0400083">심판수수료</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400482&amp;parntMenuCd2=SCD0400058">심판서식</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iptContentView.do?menuCd=SCD0400085">심판서류 발급 신청</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/topMenuLink.do?menuCd=SCD0400086">구술심리일정/방청신청</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/topMenuLink.do?menuCd=SCD0400088">단체견학 안내 및 신청</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
					
						</ul>
					</li>
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes start -->
            		<li class="th1"><a href="/ipt/topMenuLink.do?menuCd=SCD0400059"><span>책자/통계</span></a>
              			<ul class="depth2">
              		<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400485&amp;parntMenuCd2=SCD0400059">심판통계</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400486&amp;parntMenuCd2=SCD0400059">소송통계</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400487&amp;parntMenuCd2=SCD0400059">심판연구자료</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400488&amp;parntMenuCd2=SCD0400059">법령자료</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/topMenuLink.do?menuCd=SCD0400489">발간자료</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400496&amp;parntMenuCd2=SCD0400059">교육자료</a></li>
						
					
						</ul>
					</li>
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes start -->
            		<li class="th1"><a href="/ipt/topMenuLink.do?menuCd=SCD0400060"><span>특허심판원 소개</span></a>
              			<ul class="depth2">
              		<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iptContentView.do?menuCd=SCD0400096">원장 인사말</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iptContentView.do?menuCd=SCD0400097">역대 심판원장</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iptContentView.do?menuCd=SCD0400098">주요연혁</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/topMenuLink.do?menuCd=SCD0400563">부서소개/직원안내</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iptContentView.do?menuCd=SCD0400099">홍보관</a></li>
						
					<!-- 2depth loop start -->
	              		
	             		
	             		
	             		
	             		
	             		
	             		
	             		
						
							
			              	
			              		
			              		
			              		
			              		
			              		
			              		
			              	
		              	
							<li class="th2"><a href="/ipt/iptContentView.do?menuCd=SCD0400100">찾아오시는 길</a></li>
						
					
						</ul>
					</li>
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop start -->
          	<!-- 1depth child no end -->
            <!-- 1dpeth child yes end -->
          <!-- 1depth loop end -->
				</ul>
				<div class="kipo_link">
					
					<a href="https://www.moip.go.kr/" title="지식재산처 바로가기(새창)" target="_blank"><img src="/resource/images/g_logo.png?v=2025100101" alt="정부상징로고"/> 지식재산처</a>
					<a href="https://www.patent.go.kr/" title="특허로 바로가기(새창)" target="_blank"><img src="/resource/images/g_logo.png?v=2025100101" alt="정부상징로고"/> 특허로</a>
					<a href="https://www.koipa.re.kr/" title="산업재산권 분쟁조정위원회 바로가기(새창)" target="_blank"><img src="/resource/images/g_logo.png?v=2025100101" alt="정부상징로고"/> 산업재산권 분쟁조정위원회</a>
				</div>
				<div class="sitemap-menu"><a href="/kipo/siteMap.do" class="sitemap_btn" title="바로가기 (새창)" target="_blank"><em></em>전체메뉴 열기</a></div> 
			</div>
		</div>
		<div class="all-menu-btn"><a href="#" class="mMenu_btn"><em></em>모바일메뉴</a></div>
	</div>
</header>

<!-- 모바일메뉴 : s -->
<nav id="mMenu">
	<div class="mMenu_mem">
		<h1 class="logo"><a href="/ipt">특허심판원</a></h1>
	</div>
	<ul class="mMenu_list">
		<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes start -->
		<li><a href="#">특허심판제도 안내</a>
			<ul>
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iptContentView.do?menuCd=SCD0400062">특허심판이란</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes start -->
				<li><a href="/ipt/topMenuLink.do?menuCd=SCD0400061">특허심판의 종류</a>
					<ul>
		   				
			   				
			   				
			   				
			   				
			   				
			   				
			   				
			            	
			            		
			            		
			            		
			            		
			            		
			            		
			            	
						<li><a href="/ipt/iptContentView.do?menuCd=SCD0400068">개요</a></li>
						
			   				
			   				
			   				
			   				
			   				
			   				
			   				
			            	
			            		
			            		
			            		
			            		
			            		
			            		
			            	
						<li><a href="/ipt/iptContentView.do?menuCd=SCD0400069">결정계 심판</a></li>
						
			   				
			   				
			   				
			   				
			   				
			   				
			   				
			            	
			            		
			            		
			            		
			            		
			            		
			            		
			            	
						<li><a href="/ipt/iptContentView.do?menuCd=SCD0400070">당사자계 심판</a></li>
						
					</ul>
				</li>
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes start -->
				<li><a href="/ipt/topMenuLink.do?menuCd=SCD0400063">특허심판의 절차</a>
					<ul>
		   				
			   				
			   				
			   				
			   				
			   				
			   				
			   				
			            	
			            		
			            		
			            		
			            		
			            		
			            		
			            	
						<li><a href="/ipt/iptContentView.do?menuCd=SCD0400071">개요</a></li>
						
			   				
			   				
			   				
			   				
			   				
			   				
			   				
			            	
			            		
			            		
			            		
			            		
			            		
			            		
			            	
						<li><a href="/ipt/iptContentView.do?menuCd=SCD0400072">흐름도</a></li>
						
					</ul>
				</li>
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes start -->
				<li><a href="/ipt/topMenuLink.do?menuCd=SCD0400064">특허취소신청제도</a>
					<ul>
		   				
			   				
			   				
			   				
			   				
			   				
			   				
			   				
			            	
			            		
			            		
			            		
			            		
			            		
			            		
			            	
						<li><a href="/ipt/iptContentView.do?menuCd=SCD0400073">절차 개요</a></li>
						
			   				
			   				
			   				
			   				
			   				
			   				
			   				
			            	
			            		
			            		
			            		
			            		
			            		
			            		
			            	
						<li><a href="/ipt/iptContentView.do?menuCd=SCD0400074">주요내용</a></li>
						
					</ul>
				</li>
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iptContentView.do?menuCd=SCD0400065">재심</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iptContentView.do?menuCd=SCD0400066">심결취소소송</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iptContentView.do?menuCd=SCD0400067">국선대리인 제도</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iptContentView.do?menuCd=SCD0401383">심판-조정연계 제도</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->				
        	</ul>
		</li>
			<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes start -->
		<li><a href="#">소식알림</a>
			<ul>
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400476&parntMenuCd2=SCD0400056">심판원 알림사항</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0401342&parntMenuCd2=SCD0400056">보도자료</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400478&parntMenuCd2=SCD0400056">우리원 주요심결</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400479&parntMenuCd2=SCD0400056">판례연구 우수논문집</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iptContentView.do?menuCd=SCD0400075">논문공모 명예의 전당</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0401170&parntMenuCd2=SCD0400056">특허심판원 연보</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iptContentView.do?menuCd=SCD0401353">올해의 심판관</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->				
        	</ul>
		</li>
			<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes start -->
		<li><a href="#">민원/참여</a>
			<ul>
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iframe.do?menuCd=SCD0400480">민원신청</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iframe.do?menuCd=SCD0400481">나의민원확인</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iptContentView.do?menuCd=SCD0400083">심판수수료</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400482&parntMenuCd2=SCD0400058">심판서식</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iptContentView.do?menuCd=SCD0400085">심판서류 발급 신청</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes start -->
				<li><a href="/ipt/topMenuLink.do?menuCd=SCD0400086">구술심리일정/방청신청</a>
					<ul>
		   				
			   				
			   				
			   				
			   				
			   				
			   				
			   				
			            	
			            		
			            		
			            		
			            		
			            		
			            		
			            	
						<li><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400087&parntMenuCd2=SCD0400086">구술심리일정안내</a></li>
						
			   				
			   				
			   				
			   				
			   				
			   				
			   				
			            	
			            		
			            		
			            		
			            		
			            		
			            		
			            	
						<li><a href="/ipt/individualApplication.do?menuCd=SCD0400483&parntMenuCd2=SCD0400086">구술심리방청신청</a></li>
						
					</ul>
				</li>
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes start -->
				<li><a href="/ipt/topMenuLink.do?menuCd=SCD0400088">단체견학 안내 및 신청</a>
					<ul>
		   				
			   				
			   				
			   				
			   				
			   				
			   				
			   				
			            	
			            		
			            		
			            		
			            		
			            		
			            		
			            	
						<li><a href="/ipt/iptContentView.do?menuCd=SCD0400089">단체견학안내</a></li>
						
			   				
			   				
			   				
			   				
			   				
			   				
			   				
			            	
			            		
			            		
			            		
			            		
			            		
			            		
			            	
						<li><a href="/ipt/groupApplication.do?menuCd=SCD0400484&parntMenuCd2=SCD0400088">단체견학신청</a></li>
						
					</ul>
				</li>
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->				
        	</ul>
		</li>
			<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes start -->
		<li><a href="#">책자/통계</a>
			<ul>
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400485&parntMenuCd2=SCD0400059">심판통계</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400486&parntMenuCd2=SCD0400059">소송통계</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400487&parntMenuCd2=SCD0400059">심판연구자료</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400488&parntMenuCd2=SCD0400059">법령자료</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes start -->
				<li><a href="/ipt/topMenuLink.do?menuCd=SCD0400489">발간자료</a>
					<ul>
		   				
			   				
			   				
			   				
			   				
			   				
			   				
			   				
			            	
			            		
			            		
			            		
			            		
			            		
			            		
			            	
						<li><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400490&parntMenuCd2=SCD0400489">심판편람</a></li>
						
			   				
			   				
			   				
			   				
			   				
			   				
			   				
			            	
			            		
			            		
			            		
			            		
			            		
			            		
			            	
						<li><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400491&parntMenuCd2=SCD0400489">구술심리 매뉴얼</a></li>
						
			   				
			   				
			   				
			   				
			   				
			   				
			   				
			            	
			            		
			            		
			            		
			            		
			            		
			            		
			            	
						<li><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400492&parntMenuCd2=SCD0400489">소송수행 업무편람</a></li>
						
			   				
			   				
			   				
			   				
			   				
			   				
			   				
			            	
			            		
			            		
			            		
			            		
			            		
			            		
			            	
						<li><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400493&parntMenuCd2=SCD0400489">심결취소 소송정리집</a></li>
						
			   				
			   				
			   				
			   				
			   				
			   				
			   				
			            	
			            		
			            		
			            		
			            		
			            		
			            		
			            	
						<li><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400494&parntMenuCd2=SCD0400489">상표디자인 판결문 요지집</a></li>
						
			   				
			   				
			   				
			   				
			   				
			   				
			   				
			            	
			            		
			            		
			            		
			            		
			            		
			            		
			            	
						<li><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400495&parntMenuCd2=SCD0400489">기타</a></li>
						
					</ul>
				</li>
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400496&parntMenuCd2=SCD0400059">교육자료</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->				
        	</ul>
		</li>
			<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes start -->
		<li><a href="#">특허심판원 소개</a>
			<ul>
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iptContentView.do?menuCd=SCD0400096">원장 인사말</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iptContentView.do?menuCd=SCD0400097">역대 심판원장</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iptContentView.do?menuCd=SCD0400098">주요연혁</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes start -->
				<li><a href="/ipt/topMenuLink.do?menuCd=SCD0400563">부서소개/직원안내</a>
					<ul>
		   				
			   				
			   				
			   				
			   				
			   				
			   				
			   				
			            	
			            		
			            		
			            		
			            		
			            		
			            		
			            	
						<li><a href="/ipt/iptOrgMgmt1.do?menuCd=SCD0400564&parntMenuCd2=SCD0400563">부서소개 및 직원안내</a></li>
						
			   				
			   				
			   				
			   				
			   				
			   				
			   				
			            	
			            		
			            		
			            		
			            		
			            		
			            		
			            	
						<li><a href="/ipt/iptOrgMgmt2.do?menuCd=SCD0400565&parntMenuCd2=SCD0400563">특허심판원</a></li>
						
			   				
			   				
			   				
			   				
			   				
			   				
			   				
			            	
			            		
			            		
			            		
			            		
			            		
			            		
			            	
						<li><a href="/ipt/iptOrgMgmt3.do?menuCd=SCD0400566&parntMenuCd2=SCD0400563">심판부</a></li>
						
			   				
			   				
			   				
			   				
			   				
			   				
			   				
			            	
			            		
			            		
			            		
			            		
			            		
			            		
			            	
						<li><a href="/ipt/iptOrgMgmt4.do?menuCd=SCD0400567&parntMenuCd2=SCD0400563">심판정책과</a></li>
						
			   				
			   				
			   				
			   				
			   				
			   				
			   				
			            	
			            		
			            		
			            		
			            		
			            		
			            		
			            	
						<li><a href="/ipt/iptOrgMgmt5.do?menuCd=SCD0400568&parntMenuCd2=SCD0400563">송무과</a></li>
						
					</ul>
				</li>
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iptContentView.do?menuCd=SCD0400099">홍보관</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->
				
				
				
				
				
				
				
				
				
			  	
			  		
			  		
			  		
			  		
			  		
			  		
			  	
				<!-- 2depth child no start -->
				<li><a href="/ipt/iptContentView.do?menuCd=SCD0400100">찾아오시는 길</a></li>
				<!-- 2depth child no end -->
				<!-- 2depth child yes end -->
			<!-- 2depth loop start -->				
        	</ul>
		</li>
			<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop start -->
			<!-- 1depth child no end -->
      		<!-- 1depth child yes end -->
      	<!-- 1depth loop end -->
      		
			<li><a href="https://www.moip.go.kr/" title="지식재산처" target="_blank">지식재산처</a></li>
			<li><a href="https://www.patent.go.kr/" title="특허로" target="_blank">특허로</a></li>	
			<li><a href="https://www.koipa.re.kr/" title="산업재산권 분쟁조정위원회" target="_blank">산업재산권<br>분쟁조정위원회</a></li>
	</ul>
	<a href="#" class="mMenu_close">메뉴 닫기</a> 
</nav>
<!-- 모바일메뉴 : e --> 
  	<!-- //header E-->
  	
	<!-- container -->
	<div id="container">
		<div class="layout_bg"></div>
		<div class="layout">
			
			<!-- Left메뉴 : s -->
			


<script>

function linkOpen2(target, url){
	if(target == '10301'){
		location.href = url;
	}else if(target == '10302'){
		window.open(url);
	}
}

</script>

<div id="lnb">

	<h2>민원/참여</h2>
	
	<ul class="lnbMenu">
	<!-- 2depth loop start -->
		
		<!-- child no start -->
		
       		
       		
       		
       		
       		<li><a href="/ipt/iframe.do?menuCd=SCD0400480" >민원신청</a></li>
       	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
		
		<!-- child no start -->
		
       		
       		
       		
       		
       		<li><a href="/ipt/iframe.do?menuCd=SCD0400481" >나의민원확인</a></li>
       	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
		
		<!-- child no start -->
		
       		<li><a href="/ipt/iptContentView.do?menuCd=SCD0400083" class="on">심판수수료</a></li>
       		
       		
       		
       		
       	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
		
		<!-- child no start -->
		
       		
       		<li><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400482" >심판서식</a></li>
       		
       		
       		
       	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
		
		<!-- child no start -->
		
       		<li><a href="/ipt/iptContentView.do?menuCd=SCD0400085" >심판서류 발급 신청</a></li>
       		
       		
       		
       		
       	
		<!-- child no end -->
		
		<!-- child yes end -->
		
	<!-- 2depth loop start -->
		
		<!-- child no end -->
		
		<!-- child yes start -->
		<li><a href="SCD0400086">구술심리일정/방청신청</a>
			<ul>
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
           		
           		
           		<li><a href="/ipt/iptBultnMgmt.do?menuCd=SCD0400087&parntMenuCd2=SCD0400086" >구술심리일정안내</a></li>
           		
           		
           		
           	
			<!-- 3depth child no end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
           		
           		
           		
           		<li><a href="/ipt/individualApplication.do?menuCd=SCD0400483&parntMenuCd2=SCD0400086" >구술심리방청신청</a></li>
           		
           		
           	
			<!-- 3depth child no end -->
			
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
		
		<!-- child yes start -->
		<li><a href="SCD0400088">단체견학 안내 및 신청</a>
			<ul>
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
           		
           		<li><a href="/ipt/iptContentView.do?menuCd=SCD0400089" >단체견학안내</a></li>
           		
           		
           		
           		
           	
			<!-- 3depth child no end -->
			
			<!-- 3depth loop start -->
			
			
			
			
			
			
			
			
			
			<!-- 3depth child no start -->
			
           		
           		
           		
           		<li><a href="/ipt/groupApplication.do?menuCd=SCD0400484&parntMenuCd2=SCD0400088" >단체견학신청</a></li>
           		
           		
           	
			<!-- 3depth child no end -->
			
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
		
	<!-- 2depth loop end -->
	</ul>
</div>
			<!-- Left메뉴 : e -->
			
			<div id="content">
				<div class="locate">
					<h2 data-brl-use="PT">심판수수료</h2>
					<ul class="location">
						<li class="home"><span><a href="/ipt">HOME</a></span></li>
						
						<li class="depth1">
							<span>
							
								<a href="/ipt/naviMenuLink.do?menuCd=SCD0400058">민원/참여</a>
								
							
							</span>
						</li>
						
						<li class="depth1">
							<span>
							
								
								심판수수료
							
							</span>
						</li>
						
					</ul>
					
					<div class="locate_btn">
						<button class="sns_btn" onclick="sns()"><span class="hide">sns공유하기(페이스북,X,밴드,카카오스토리)</span><i class="fa fa-share-alt" title="SNS공유하기"></i></button>
						
						
						<button class="print_btn" onclick="window.print()"><i class="fa fa-print" title="인쇄하기"></i></button>
					</div>

					<div class="sns_btns" id="sns">
						<a href="javascript:shareSNS('f','심판수수료','/ipt/iptContentView.do?menuCd=SCD0400083');" title="페이스북 심판수수료 공유하기 새창열림"><img src="/resource/images/sns_fb_b.png" alt="페이스북 공유하기"/></a>
						<a href="javascript:shareSNS('t','심판수수료','/ipt/iptContentView.do?menuCd=SCD0400083');" title="X 심판수수료 공유하기 새창열림"><img src="/resource/images/sns_tw_b.png" alt="X 공유하기"/></a>
						<a href="javascript:shareSNS('b','심판수수료','/ipt/iptContentView.do?menuCd=SCD0400083');" title="밴드 심판수수료 공유하기 새창열림"><img src="/resource/images/sns_blog_b.png" alt="밴드 공유하기"/></a>
						<a href="javascript:shareSNS('k','심판수수료','/ipt/iptContentView.do?menuCd=SCD0400083');" title="카카오스토리 심판수수료 공유하기 새창열림"><img src="/resource/images/sns_kakao_b.png" alt="카카오스토리 공유하기"/></a>
						<button class="close_btn" onclick="sns()"><i class="fa fa-times" title="SNS공유하기 닫기"></i><span class="hide">SNS공유하기 닫기</span></button>
					</div>
				</div>
				
				<article class="itxt">
					
					<!-- 내용 : s -->
					<h4 class="tit_02 mt0">심판청구료</h4>

<p class="dTxt">청구서 제출형태에 따라 심판청구료 차등적용</p>

<table class="table_type" summary="이 표는 청구서 제출형태에 따라 심판청구료입니다.">
	<caption>심판청구료</caption>
	<colgroup>
		<col style="width:22%" />
		<col style="width:26%" />
		<col style="width:26%" />
		<col style="width:26%" />
	</colgroup>
	<thead>
		<tr>
			<th scope="col">제출형태</th>
			<th scope="col">특허&middot;실용신안</th>
			<th scope="col">디자인</th>
			<th scope="col">상표</th>
		</tr>
	</thead>
	<tbody>
		<tr>
			<td>전자문서/서면</td>
			<td>매건 150,000원/170,000원</td>
			<td>1디자인마다 240,000원/260,000원</td>
			<td>직접적으로 심판청구의 이유가 있는<br />
			상품류마다 240,000원 / 250,000원</td>
		</tr>
		<tr>
			<td>가산료</td>
			<td>1항마다 15,000원</td>
			<td>없음</td>
			<td>1상품류의 지정상품이 10개 초과하는 경우 초과 지정상품마다 2천원 가산<br />
			(2023.8.1. 이후 출원건부터 적용)</td>
		</tr>
	</tbody>
</table>

<p class="dTit mt10">다만, 다음 심판의 경우에는 심판청구의 이유가 있는 청구항, 디자인 또는 상품구분에 한하여 위와 같이 계산됩니다.</p>

<ul class="list_01">
	<li>특허&middot;실용신안 거절결정불복심판 (단, <span style="text-align: left; color: rgb(85, 85, 85); text-transform: none; text-indent: 0px; letter-spacing: -0.5px; font-family: &quot;Malgun Gothic&quot;, &quot;맑은 고딕&quot;, 굴림, gulim, 돋움, dotum, &quot;Microsoft NeoGothic&quot;, &quot;Droid sans&quot;, sans-serif; font-size: 14px; font-style: normal; font-weight: 400; word-spacing: 0px; float: none; display: inline !important; white-space: normal; orphans: 2; widows: 2; background-color: rgb(255, 255, 255); text-decoration-style: initial; font-variant-ligatures: normal; font-variant-caps: normal; -webkit-text-stroke-width: 0px; text-decoration-thickness: initial; text-decoration-color: initial;">①</span><span style="text-align: left; color: rgb(85, 85, 85); text-transform: none; text-indent: 0px; letter-spacing: -0.5px; font-family: &quot;Malgun Gothic&quot;, &quot;맑은 고딕&quot;, 굴림, gulim, 돋움, dotum, &quot;Microsoft NeoGothic&quot;, &quot;Droid sans&quot;, sans-serif; font-size: 14px; font-style: normal; font-weight: 400; word-spacing: 0px; float: none; display: inline !important; white-space: normal; orphans: 2; widows: 2; background-color: rgb(255, 255, 255); text-decoration-style: initial; font-variant-ligatures: normal; font-variant-caps: normal; -webkit-text-stroke-width: 0px; text-decoration-thickness: initial; text-decoration-color: initial;"></span>거절결정서에 최종 거절결정한 청구항이 기재되지 않은 경우 <span style="text-align: left; color: rgb(85, 85, 85); text-transform: none; text-indent: 0px; letter-spacing: -0.5px; font-family: &quot;Malgun Gothic&quot;, &quot;맑은 고딕&quot;, 굴림, gulim, 돋움, dotum, &quot;Microsoft NeoGothic&quot;, &quot;Droid sans&quot;, sans-serif; font-size: 14px; font-style: normal; font-weight: 400; word-spacing: 0px; float: none; display: inline !important; white-space: normal; orphans: 2; widows: 2; background-color: rgb(255, 255, 255); text-decoration-style: initial; font-variant-ligatures: normal; font-variant-caps: normal; -webkit-text-stroke-width: 0px; text-decoration-thickness: initial; text-decoration-color: initial;">②</span>청구항을 기재하지 않는 거절결정이유가 포함된 경우 <span style="text-align: left; color: rgb(85, 85, 85); text-transform: none; text-indent: 0px; letter-spacing: -0.5px; font-family: &quot;Malgun Gothic&quot;, &quot;맑은 고딕&quot;, 굴림, gulim, 돋움, dotum, &quot;Microsoft NeoGothic&quot;, &quot;Droid sans&quot;, sans-serif; font-size: 14px; font-style: normal; font-weight: 400; word-spacing: 0px; float: none; display: inline !important; white-space: normal; orphans: 2; widows: 2; background-color: rgb(255, 255, 255); text-decoration-style: initial; font-variant-ligatures: normal; font-variant-caps: normal; -webkit-text-stroke-width: 0px; text-decoration-thickness: initial; text-decoration-color: initial;">③</span>2009.6.30.이전 출원되어 거절결정된 경우는 전체 청구항수를 기준으로 계산)</li>
	<li>취소결정불복심판</li>
	<li>무효심판</li>
	<li>권리범위확인심판</li>
	<li>통상실시권허여심판</li>
	<li>특허권존속기간연장등록의 무효심판</li>
	<li>상표등록의 취소심판</li>
	<li>상표권존속기간갱신등록의 무효심판</li>
	<li>상표사용권등록의 취소심판</li>
	<li>상품분류전환등록의 무효심판</li>
</ul>

<p class="dTit">보정각하결정불복심판 청구료</p>

<ul class="list_01">
	<li>전자문서(온라인)제출 : 200,000원</li>
	<li>서면제출 : 220,000원</li>
</ul>

<p class="dTit">상품분류전환등록신청에 대한 거절결정불복심판 청구료</p>

<ul class="list_01">
	<li>전자문서(온라인)제출 : 250,000원</li>
	<li>서면제출 : 270,000원</li>
</ul>

<p class="dTit">심판청구료 감면</p>

<p class="dTxt">개인(발명자&middot;고안자 또는 창작자와 출원인이 같은 경우에만 해당한다),소기업 또는 중기업이 자신의 특허권 등에 대하여 권리범위확인심판을 청구하는 경우에는 심판청구료의 100분의 70, 전담조직의 경우에는 심판청구료의 100분의 50 감면(100원 미만의 금액은 버림)</p>

<p class="dTit">특허취소신청 수수료</p>

<ul class="list_01">
	<li>전자문서(온라인)제출 :&nbsp; 매건 50,0000원 +&nbsp;청구범위 1항마다 5천원 가산</li>
	<li>서면제출 : 매건 60,000원 +&nbsp;청구범위 1항마다 5천원 가산</li>
</ul>

<h4 class="tit_02">참가신청료</h4>

<p class="dTit">당사자 참가</p>

<p class="dTxt">매건당 전자 142,000원/서면 150,000원</p>

<p class="dTit">보조참가</p>

<p class="dTxt">매건당 전자 16,000원/서면 18,000원</p>

<h4 class="tit_02">보정료</h4>

<p class="dTxt">보정료는 보정서 제출형태에 따라 차등적용되며, 자진보정의 경우에도 납부하여야 합니다.</p>

<p class="dTit">전자문서 제출</p>

<p class="dTxt">매건 4,000원, 서면 제출 : 매건 14,000원</p>

<p class="dTit">보정료 납부대상</p>

<ul class="list_01">
	<li>위임장 미제출 등 대리권증명서류의 미비</li>
	<li>심판청구의 이유 미제출</li>
	<li>번역문 미제출</li>
	<li>정정명세서 미제출(정정심판에 한함)</li>
	<li>(가)호 도면 및 그 설명서 미제출(권리범위확인심판에 한함)</li>
	<li>정정심판 또는 정정청구시 실시권자의동의서 미제출</li>
</ul>

<h4 class="tit_02">심사전치시 추가심사청구료</h4>

<p class="dTxt">새로운 청구범위의 항이 신설되어 그 항에 대한 심사청구료가 추가된 경우 신설된 1항마다 40,000원 가산</p>

<h4 class="tit_02">법정기간&middot;지정기간연장 신청료</h4>

<ul class="list_02">
	<li>1회 : 20,000원</li>
	<li>2회 : 30,000원</li>
	<li>3회 : 60,000원</li>
	<li>4회 : 120,000원</li>
	<li>5회이상 : 240,000원</li>
</ul>

<h4 class="tit_02">비용액결정 청구료</h4>

<p class="dTxt">매건 500원</p>

<h4 class="tit_02">집행문 정본의 청구료</h4>

<p class="dTxt">매건 400원</p>

<h4 class="tit_02">심판관 기피신청료</h4>

<p class="dTxt">매건당 전자 1,000원/서면 1,500원</p>

<h4 class="tit_02">정정청구료</h4>

<p class="dTit">전자문서 (온라인)</p>

<p class="dTxt">30,000원에 청구범위 1항마다 7,000원 가산한 금액</p>

<p class="dTit">서면</p>

<p class="dTxt">40,000원에 청구범위 1항마다 7,000원을 가산한 금액</p>

<ul class="list_03">
	<li>다만, 이의신청 또는 실용신안기술평가와 관련되는 정정청구의 경우에는 전자문서 제출시 매건 26,000원, 서면 제출시 매건 36,000원</li>
	<li>특허심판원에 계속 중인 다른 무효심판절차 또는 정정의 무효심판절차에서 제출한 정정청구서와 동일한 내용의 정정청구서를 제출하는 경우 : 면제</li>
</ul>

<h4 class="tit_02">구술심리를 녹취한 테이프의 복사신청료</h4>

<p class="dTxt">매건 10,000원</p>

<h4 class="tit_02">수수료 납부방법 안내</h4>

<p class="dTxt">수수료 납부방법은 3가지 방법이 있습니다.</p>

<p class="dTit">온라인수수료 납부</p>

<p class="dTxt">지식재산처홈페이지 &rarr; 특허로 &rarr; 수수료관리 &rarr; 수수료납부에서 납부하실 수 있습니다.</p>

<p class="dTit">은행 방문</p>

<p class="dTxt">은행방문을 통한 수수료 납부(서면)</p>

<p class="dTit">우편 제출</p>

<p class="dTxt">우편으로 제출코자 하는 경우 통상환 증서를 동봉하여 제출하시면 됩니다.</p>

          			<!-- 내용 : e -->
					
					<!-- 담당자 : s -->
					



<div class="name_tel">
	
	
        <ul class="user_info">
			<li>상담 : 상담센터(1544-8080)</li>
			<li>담당부서 : 심판정책과</li>
			<li>담당자 : 김민선</li>
			<li>전화번호 : 042-481-5282</li>
		</ul>
	
				
</div>

          			<!-- 담당자 : e -->
          			
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
			<li><a href="/kipo/kipoContentView.do?menuCd=SCD0200539" target="_blank" title="홈페이지이용안내 바로가기 (새창)">홈페이지이용안내</a></li>
			<li><a href="/kipo/kipoContentView.do?menuCd=SCD0200540" target="_blank" title="특허서비스헌장 바로가기 (새창)">특허서비스헌장</a></li>
			<li><a href="/ipt/iptContentView.do?menuCd=SCD0400100" target="_blank" title="찾아오시는길 바로가기 (새창)">찾아오시는길</a></li>
			<li><a href="mailto:master_ipt@korea.kr" title="운영자에게메일보내기 (새창)">운영자에게메일보내기</a></li>
			<li><a href="https://www.mois.go.kr/frt/sub/popup/p_taegugki_banner/screen.do" target="_blank" title="국가상징알아보기 바로가기 (새창)"><img src="/resource/images/kipo_header_flag.png">국가상징알아보기</a></li>
       </ul>
  	</div>
</div>

<div class="footer_bottom">
	<div class="layout">
		
		<h1 class="footer_logo"><span class="hide">특허심판원</span></h1>
		<address>
			
			<p>35208 대전광역시 서구 청사로 189 정부대전청사 민원동<span>특허민원상담센터(특허고객상담센터) 1544-8080(유료 / 월~금 09:00~18:00, 공휴일 제외)</span></p>
			<p class="copy">COPYRIGHT (C) Intellectual Property Trial and Appeal Board. All Rights Reserved</p> 
		</address>
	</div>
</div>
	
	</footer>
	<!--// footer E-->
	
</div>
</body>
</html>


