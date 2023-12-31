from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sqlalchemy import create_engine
from artist_data_loader import artist_DataLoader
from sklearn.metrics.pairwise import cosine_similarity
import random
from django.contrib.sessions.models import Session
from user.models import MMLUserInfo
import time

engine = create_engine('mysql+pymysql://admin:pizza715@mml.cu4cw1rqzfei.ap-northeast-2.rds.amazonaws.com/mml?charset=utf8')
pd.set_option('mode.chained_assignment', None)

# DataLoader 인스턴스 생성
artist_data_loader = artist_DataLoader(engine)

mml_music_info_df, mml_artist_gen_df, mml_user_like_artist_df = artist_data_loader.artist_load_data()


class user_like_artist_view(APIView):
    def get(self, request):
        print('==========User_like_artist 실행==========')
        # 코드 시작 부분
        start_time = time.time()

        session_key = request.COOKIES.get("sessionid")
    
        if session_key:
            try:
                # 데이터베이스에서 세션 객체 검색
                session = Session.objects.get(session_key=session_key)
                # 세션 데이터 디코딩
                session_data = session.get_decoded()
                # 세션 데이터 출력
                print("Session Data:", session_data)
                session_id = session_data.get("_auth_user_id")
                # 세션 데이터에서 특정 값 접근
                user = MMLUserInfo.objects.get(pk=session_id)
                user_id = str(user)
                print("User ID from session:", user_id)
                
                # 여기에 추가 로직
            except Session.DoesNotExist:
                print("Session with key does not exist")
        else:
            print("Session key does not exist")
            
        # 데이터 전처리
        # 사용자가 좋아하는 아티스트 데이터와 아티스트 장르 데이터를 병합하여 좋아하는 아티스트의 장르를 구합니다.
        merged_data = pd.merge(mml_user_like_artist_df, mml_artist_gen_df, on='artist', how='left')

        # 사용자별로 데이터를 그룹화하고 좋아하는 모든 장르, 성별, 연령 그룹을 연결합니다.
        user_genre_df = merged_data.groupby('user_id').agg({
            'genre': lambda x: ' '.join(x.dropna()),
            'gen': 'first',    # 가정: 모든 행에 대해 동일한 값이 존재한다고 가정
            'age_group': 'first'  # 가정: 모든 행에 대해 동일한 값이 존재한다고 가정
        }).reset_index()


        # ITF-IDF 벡터 구현
        tfidf = TfidfVectorizer(stop_words='english')
        tfidf_matrix = tfidf.fit_transform(user_genre_df['genre'])

        # 코사인 유사도 계산
        cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

        # 사용자 ID를 기반으로 노래를 추천하는 기능 (성별 및 연령대 필터링 적용)
        def recommend_songs(user_id, num_recommendations=5):
            # 사용자 id와 동일한 성별 및 연령대를 가진 사용자들만 필터링
            target_user_data = user_genre_df[user_genre_df['user_id'] == user_id]
            if target_user_data.empty:
                return "사용자 ID를 찾을 수 없습니다."

            target_gen = target_user_data['gen'].iloc[0]
            target_age_group = target_user_data['age_group'].iloc[0]

            filtered_users = user_genre_df[(user_genre_df['gen'] == target_gen) &
                                        (user_genre_df['age_group'] == target_age_group)]

            # 필터링된 사용자들의 인덱스 추출
            filtered_user_indices = filtered_users.index.tolist()

            # 해당 사용자와 필터링된 사용자들의 유사성 점수를 가져옵니다.
            idx = user_genre_df.index[user_genre_df['user_id'] == user_id].tolist()[0]
            sim_scores = list(enumerate(cosine_sim[idx]))

            # 유사성 점수 중에서 필터링된 사용자들만을 대상으로 정렬
            sim_scores = [sim_score for sim_score in sim_scores if sim_score[0] in filtered_user_indices]
            sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

            # 가장 유사한 사용자들의 점수
            sim_scores = sim_scores[1:num_recommendations+1]

            # 사용자 인덱스
            user_indices = [i[0] for i in sim_scores]

            # 가장 유사한 사용자들 반환
            return user_genre_df['user_id'].iloc[user_indices]
        
        recommended_users = recommend_songs(user_id)

        # 이제 추천 함수를 다시 실행하여 테스트 사용자와 유사한 사용자를 찾을 수 있습니다.
        recommended_user_ids = recommend_songs(user_id).tolist()

        # 유사한 사용자들이 선호하는 아티스트 찾기
        preferred_artists = mml_user_like_artist_df[mml_user_like_artist_df['user_id'].isin(recommended_user_ids)]['artist'].unique()

        def get_all_songs_for_artists(artist_list):
            songs_dict = {}
            for artist in artist_list:
                # 해당 아티스트의 모든 노래만 필터링
                artist_songs = mml_music_info_df[mml_music_info_df['artist'] == artist]
                # 노래가 존재하는 경우에만 딕셔너리에 추가
                if not artist_songs.empty:
                    songs_dict[artist] = artist_songs['title'].tolist()
            return songs_dict

        # 모든 추천된 아티스트별로 모든 노래를 가져옵니다.
        artist_songs_dict = get_all_songs_for_artists(preferred_artists)

        # 아티스트당 최대 노래 수 제한
        MAX_SONGS_PER_ARTIST = 3

        # 아티스트별 랜덤 노래 선택 부분 전에 시드 값을 설정
        random.seed(123) # 여기서 123은 예시 값이며, 원하는 어떤 정수 값이든 사용할 수 있습니다.

        # 각 아티스트별로 최대 노래 수만큼 노래 선택
        limited_songs_with_artists = []
        for artist, songs in artist_songs_dict.items():
            selected_songs = random.sample(songs, min(MAX_SONGS_PER_ARTIST, len(songs)))
            for song in selected_songs:
                limited_songs_with_artists.append((artist, song))
                
        # 전체 리스트에서 랜덤으로 20곡 선택
        random.seed(123) # 동일한 시드 값으로 다시 설정
        selected_songs_with_artists = random.sample(limited_songs_with_artists, min(20, len(limited_songs_with_artists)))

        # 선택된 노래와 아티스트를 데이터프레임으로 변환
        df_selected_songs_with_artists = pd.DataFrame(selected_songs_with_artists, columns=['artist', 'title'])

        # 'Title'과 'Artist'를 기준으로 데이터프레임을 병합하여 일치하는 노래 찾기
        user_like_artist_final = pd.merge(
            mml_music_info_df, df_selected_songs_with_artists,
            on=['title', 'artist'],
            how='inner'
        )

        user_like_artist_final = user_like_artist_final[['title', 'artist', 'album_image_url']]

        user_like_artist_results=[]

        for index,row in user_like_artist_final.iterrows():
            result = {
                'title': row['title'],
                'artist': row['artist'],
                'image': row['album_image_url']
            }
            user_like_artist_results.append(result)
            
        # 코드 끝 부분
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"선호가수 기반 코드 실행 시간: {execution_time}초")
        return Response(user_like_artist_results, status=status.HTTP_200_OK)