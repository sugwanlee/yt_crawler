from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="YouTube Shorts Crawler API",
        default_version='v1',
        description="YouTube Shorts 크롤링을 위한 API 문서",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# CrawlShorts API 문서화
crawl_shorts_get = swagger_auto_schema(
    operation_summary="크롤링 작업 조회",
    operation_description="등록된 모든 크롤링 작업을 조회합니다.",
    responses={
        200: openapi.Response(
            description="작업 조회 성공",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example="모든 크롤링 작업 조회"),
                    'tasks': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER, example=5),
                                'name': openapi.Schema(type=openapi.TYPE_STRING, example="task1"),
                                'task': openapi.Schema(type=openapi.TYPE_STRING, example="youtube_crawling.tasks.crawl_channels_task"),
                                'args': openapi.Schema(type=openapi.TYPE_STRING, example='[["https://www.youtube.com/@%EC%B9%A1%EC%B4%89"], "task1"]'),
                                'kwargs': openapi.Schema(type=openapi.TYPE_STRING, example="{}"),
                                'queue': openapi.Schema(type=openapi.TYPE_STRING, nullable=True, example=None),
                                'exchange': openapi.Schema(type=openapi.TYPE_STRING, nullable=True, example=None),
                                'routing_key': openapi.Schema(type=openapi.TYPE_STRING, nullable=True, example=None),
                                'headers': openapi.Schema(type=openapi.TYPE_STRING, example="{}"),
                                'priority': openapi.Schema(type=openapi.TYPE_STRING, nullable=True, example=None),
                                'expires': openapi.Schema(type=openapi.TYPE_STRING, nullable=True, example=None),
                                'expire_seconds': openapi.Schema(type=openapi.TYPE_INTEGER, example=43200),
                                'one_off': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                                'start_time': openapi.Schema(type=openapi.TYPE_STRING, nullable=True, example=None),
                                'enabled': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                                'last_run_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', example="2025-06-01T03:59:25.437135+09:00"),
                                'total_run_count': openapi.Schema(type=openapi.TYPE_INTEGER, example=2),
                                'date_changed': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', example="2025-06-01T04:52:22.590609+09:00"),
                                'description': openapi.Schema(type=openapi.TYPE_STRING, example=""),
                                'interval': openapi.Schema(type=openapi.TYPE_STRING, nullable=True, example=None),
                                'crontab': openapi.Schema(type=openapi.TYPE_INTEGER, example=4),
                                'solar': openapi.Schema(type=openapi.TYPE_STRING, nullable=True, example=None),
                                'clocked': openapi.Schema(type=openapi.TYPE_STRING, nullable=True, example=None)
                            }
                        )
                    )
                }
            )
        ),
        400: openapi.Response(
            description="작업 조회 실패",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example="'NoneType' object has no attribute 'get'")
                }
            )
        )
    }
)

crawl_shorts_post = swagger_auto_schema(
    operation_summary="크롤링 작업 등록",
    operation_description="새로운 크롤링 작업을 등록합니다.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['urls', 'task_name', 'minute', 'hour'],
        properties={
            'urls': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(type=openapi.TYPE_STRING),
                example=["https://youtube.com/channel/...", "https://youtube.com/channel/..."]
            ),
            'task_name': openapi.Schema(type=openapi.TYPE_STRING, example="daily_shorts_crawl"),
            'minute': openapi.Schema(type=openapi.TYPE_STRING, example="0"),
            'hour': openapi.Schema(type=openapi.TYPE_STRING, example="9"),
        }
    ),
    responses={
        201: openapi.Response(
            description="작업 등록 성공",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        example="주기적인 크롤링 작업이 등록되었습니다."
                    )
                }
            )
        ),
        400: openapi.Response(
            description="작업 등록 실패",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example="'urls' is required")
                }
            )
        )
    }
)

crawl_shorts_delete = swagger_auto_schema(
    operation_summary="크롤링 작업 삭제",
    operation_description="모든 크롤링 작업을 삭제합니다.",
    responses={
        200: openapi.Response(
            description="작업 삭제 성공",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        example="모든 크롤링 작업 취소"
                    )
                }
            )
        ),
        400: openapi.Response(
            description="작업 삭제 실패",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example="Failed to delete tasks")
                }
            )
        )
    }
)

# ShortsData API 문서화
shorts_data_get = swagger_auto_schema(
    operation_summary="쇼츠 정보 조회",
    operation_description="수집된 모든 쇼츠 정보를 조회합니다.",
    responses={
        200: openapi.Response(
            description="쇼츠 정보 조회 성공",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example="수집된 쇼츠 정보들 조회 완료"),
                    'data': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'stack_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', example="2024-03-20"),
                                'created_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', example="2024-03-20"),
                                'channel_name': openapi.Schema(type=openapi.TYPE_STRING, example="채널명"),
                                'video_title': openapi.Schema(type=openapi.TYPE_STRING, example="영상 제목"),
                                'video_url': openapi.Schema(type=openapi.TYPE_STRING, format='uri', example="https://youtube.com/shorts/..."),
                                'upload_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', example="2024-03-19"),
                                'video_views': openapi.Schema(type=openapi.TYPE_INTEGER, example=1000),
                                'subscriber_count': openapi.Schema(type=openapi.TYPE_INTEGER, example=10000)
                            }
                        )
                    )
                }
            )
        ),
        400: openapi.Response(
            description="쇼츠 정보 조회 실패",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example="'NoneType' object has no attribute 'get'")
                }
            )
        )
    }
)

shorts_data_delete = swagger_auto_schema(
    operation_summary="쇼츠 정보 삭제",
    operation_description="수집된 모든 쇼츠 정보를 삭제합니다.",
    responses={
        200: openapi.Response(
            description="쇼츠 정보 삭제 성공",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        example="수집된 모든 쇼츠 정보 삭제"
                    )
                }
            )
        ),
        400: openapi.Response(
            description="쇼츠 정보 삭제 실패",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, example="Failed to delete shorts data")
                }
            )
        )
    }
) 